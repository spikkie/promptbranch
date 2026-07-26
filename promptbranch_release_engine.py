from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "promptbranch.release.contract"
SCHEMA_VERSION = "1.0"
EVIDENCE_SCHEMA = "promptbranch.release.execution"
_ALLOWED_TOP = {
    "schema", "schema_version", "repository", "version_authority", "artifact",
    "operations", "preserve", "forbid_mutation", "environment", "evidence",
    "delegation",
}
_ALLOWED_OPS = {"validate", "test", "build", "verify", "publish", "adopt", "verify_current"}
_MUTATING_OPS = {"build", "publish", "adopt"}


class ReleaseContractError(ValueError):
    pass


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_relative(value: str, label: str) -> str:
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise ReleaseContractError(f"{label} must be a non-empty repository-relative path without traversal")
    return path.as_posix()


def _require_keys(obj: dict[str, Any], required: set[str], allowed: set[str], label: str) -> None:
    missing = sorted(required - set(obj))
    unknown = sorted(set(obj) - allowed)
    if missing:
        raise ReleaseContractError(f"{label} missing required fields: {', '.join(missing)}")
    if unknown:
        raise ReleaseContractError(f"{label} contains unknown fields: {', '.join(unknown)}")


def load_contract(repo: Path, config: str = ".promptbranch-release.json") -> dict[str, Any]:
    repo = repo.resolve()
    config_rel = _safe_relative(config, "config")
    path = repo / config_rel
    if not path.is_file():
        raise ReleaseContractError(f"release contract not found: {config_rel}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseContractError(f"invalid release contract: {exc}") from exc
    if not isinstance(data, dict):
        raise ReleaseContractError("release contract root must be an object")
    _require_keys(data, _ALLOWED_TOP, _ALLOWED_TOP, "contract")
    if data["schema"] != SCHEMA or data["schema_version"] != SCHEMA_VERSION:
        raise ReleaseContractError("unsupported release contract schema or schema_version")

    repository = data["repository"]
    if not isinstance(repository, dict):
        raise ReleaseContractError("repository must be an object")
    _require_keys(repository, {"repo_id"}, {"repo_id"}, "repository")
    if not isinstance(repository["repo_id"], str) or not repository["repo_id"].strip():
        raise ReleaseContractError("repository.repo_id must be a non-empty string")

    authority = data["version_authority"]
    if not isinstance(authority, dict):
        raise ReleaseContractError("version_authority must be an object")
    _require_keys(authority, {"path", "format"}, {"path", "format"}, "version_authority")
    authority["path"] = _safe_relative(authority["path"], "version_authority.path")
    if authority["format"] not in {"plain", "python", "toml"}:
        raise ReleaseContractError("version_authority.format must be plain, python, or toml")

    artifact = data["artifact"]
    if not isinstance(artifact, dict):
        raise ReleaseContractError("artifact must be an object")
    _require_keys(artifact, {"path", "kind"}, {"path", "kind", "required_root_entries"}, "artifact")
    artifact["path"] = _safe_relative(artifact["path"], "artifact.path")
    if artifact["kind"] not in {"zip", "file"}:
        raise ReleaseContractError("artifact.kind must be zip or file")
    entries = artifact.get("required_root_entries", [])
    if not isinstance(entries, list) or any(not isinstance(x, str) or "/" in x or not x for x in entries):
        raise ReleaseContractError("artifact.required_root_entries must contain root entry names")

    operations = data["operations"]
    if not isinstance(operations, dict):
        raise ReleaseContractError("operations must be an object")
    unknown_ops = sorted(set(operations) - _ALLOWED_OPS)
    if unknown_ops:
        raise ReleaseContractError(f"operations contains unknown operations: {', '.join(unknown_ops)}")
    for op_name, steps in operations.items():
        if not isinstance(steps, list):
            raise ReleaseContractError(f"operations.{op_name} must be an array")
        for index, step in enumerate(steps):
            label = f"operations.{op_name}[{index}]"
            if not isinstance(step, dict):
                raise ReleaseContractError(f"{label} must be an object")
            _require_keys(step, {"id", "argv", "timeout_seconds"}, {"id", "argv", "timeout_seconds", "cwd", "env", "accepted_exit_codes", "release_blocking"}, label)
            if not isinstance(step["id"], str) or not step["id"].strip():
                raise ReleaseContractError(f"{label}.id must be non-empty")
            argv = step["argv"]
            if not isinstance(argv, list) or not argv or any(not isinstance(x, str) or not x for x in argv):
                raise ReleaseContractError(f"{label}.argv must be a non-empty string array")
            if any(x in {"sh", "bash", "zsh", "cmd", "powershell", "pwsh"} for x in argv[:1]):
                raise ReleaseContractError(f"{label}.argv may not invoke a shell")
            timeout = step["timeout_seconds"]
            if not isinstance(timeout, (int, float)) or timeout <= 0 or timeout > 14400:
                raise ReleaseContractError(f"{label}.timeout_seconds must be within 0 < timeout <= 14400")
            step["cwd"] = _safe_relative(step.get("cwd", "."), f"{label}.cwd") if step.get("cwd", ".") != "." else "."
            env = step.get("env", {})
            if not isinstance(env, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in env.items()):
                raise ReleaseContractError(f"{label}.env must map names to non-secret literal values")
            accepted = step.get("accepted_exit_codes", [0])
            if not isinstance(accepted, list) or not accepted or any(not isinstance(x, int) for x in accepted):
                raise ReleaseContractError(f"{label}.accepted_exit_codes must be an integer array")
            step["accepted_exit_codes"] = accepted
            step["release_blocking"] = bool(step.get("release_blocking", True))

    for field in ("preserve", "forbid_mutation", "environment"):
        value = data[field]
        if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
            raise ReleaseContractError(f"{field} must be a non-empty string array or empty array")
    data["preserve"] = [_safe_relative(x, "preserve entry") for x in data["preserve"]]
    data["forbid_mutation"] = [_safe_relative(x, "forbid_mutation entry") for x in data["forbid_mutation"]]
    if ".pb_profile" not in {x.rstrip("/") for x in data["preserve"]}:
        raise ReleaseContractError("preserve must include .pb_profile/")
    if ".promptbranch-repo.json" not in data["preserve"]:
        raise ReleaseContractError("preserve must include .promptbranch-repo.json")

    evidence = data["evidence"]
    if not isinstance(evidence, dict):
        raise ReleaseContractError("evidence must be an object")
    _require_keys(evidence, {"directory"}, {"directory"}, "evidence")
    evidence["directory"] = _safe_relative(evidence["directory"], "evidence.directory")

    delegation = data["delegation"]
    if not isinstance(delegation, dict):
        raise ReleaseContractError("delegation must be an object")
    _require_keys(delegation, {"promptbranch_owns", "repository_owns"}, {"promptbranch_owns", "repository_owns"}, "delegation")
    for key in ("promptbranch_owns", "repository_owns"):
        if not isinstance(delegation[key], list) or not delegation[key]:
            raise ReleaseContractError(f"delegation.{key} must be a non-empty array")
    return data


def plan(repo: Path, contract: dict[str, Any]) -> dict[str, Any]:
    artifact = repo / contract["artifact"]["path"]
    phases = []
    for name in ("validate", "test", "build", "verify", "publish", "adopt", "verify_current"):
        steps = contract["operations"].get(name, [])
        phases.append({
            "operation": name,
            "explicit": name in {"publish", "adopt"},
            "mutating": name in _MUTATING_OPS,
            "steps": [{"id": s["id"], "argv": s["argv"], "cwd": s["cwd"], "timeout_seconds": s["timeout_seconds"]} for s in steps],
        })
    return {
        "ok": True,
        "action": "release_contract_plan",
        "status": "planned_read_only",
        "repository": contract["repository"],
        "contract_schema": contract["schema"],
        "artifact": {"path": contract["artifact"]["path"], "exists": artifact.is_file()},
        "phases": phases,
        "preserve": contract["preserve"],
        "forbid_mutation": contract["forbid_mutation"],
        "safety": {"planning_mutated_state": False, "publication_separate": True, "adoption_separate": True},
    }


def _snapshot(repo: Path, paths: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for rel in paths:
        path = repo / rel.rstrip("/")
        if path.is_file():
            result[rel] = {"kind": "file", "sha256": _sha256(path)}
        elif path.is_dir():
            result[rel] = {"kind": "directory", "exists": True}
        else:
            result[rel] = {"kind": "missing"}
    return result


def _verify_artifact(path: Path, contract: dict[str, Any]) -> dict[str, Any]:
    if not path.is_file():
        return {"ok": False, "status": "artifact_missing", "path": str(path)}
    payload = {"ok": True, "status": "artifact_verified", "path": str(path), "size_bytes": path.stat().st_size, "sha256": _sha256(path)}
    if contract["artifact"]["kind"] == "zip":
        try:
            with zipfile.ZipFile(path) as archive:
                bad = archive.testzip()
                names = archive.namelist()
                unsafe = [n for n in names if n.startswith("/") or ".." in Path(n).parts]
                roots = {Path(n).parts[0] for n in names if Path(n).parts}
        except zipfile.BadZipFile as exc:
            return {"ok": False, "status": "artifact_invalid_zip", "error": str(exc)}
        required = set(contract["artifact"].get("required_root_entries", []))
        missing = sorted(required - roots)
        if bad or unsafe or missing:
            return {"ok": False, "status": "artifact_structure_invalid", "bad_entry": bad, "unsafe_entries": unsafe, "missing_root_entries": missing}
        payload.update({"entry_count": len(names), "required_root_entries_present": True})
    return payload


def execute(repo: Path, contract: dict[str, Any], operation: str) -> dict[str, Any]:
    if operation not in _ALLOWED_OPS:
        raise ReleaseContractError(f"unsupported operation: {operation}")
    if operation in {"publish", "adopt"} and not contract["operations"].get(operation):
        raise ReleaseContractError(f"operation {operation} is not declared")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-{operation}"
    evidence_dir = repo / contract["evidence"]["directory"] / run_id
    evidence_dir.mkdir(parents=True, exist_ok=False)
    preserved_before = _snapshot(repo, contract["preserve"])
    forbidden_before = _snapshot(repo, contract["forbid_mutation"])
    results = []
    ok = True
    for index, step in enumerate(contract["operations"].get(operation, []), start=1):
        started = _utc()
        start = time.monotonic()
        stdout_path = evidence_dir / f"{index:02d}-{step['id']}.stdout.log"
        stderr_path = evidence_dir / f"{index:02d}-{step['id']}.stderr.log"
        env = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", ""), "LANG": os.environ.get("LANG", "C.UTF-8")}
        for name in contract["environment"]:
            if name in os.environ:
                env[name] = os.environ[name]
        env.update(step.get("env", {}))
        timed_out = False
        error = None
        try:
            proc = subprocess.run(step["argv"], cwd=repo / step["cwd"], env=env, text=True, capture_output=True, timeout=float(step["timeout_seconds"]), check=False)
            rc = proc.returncode
            stdout_path.write_text(proc.stdout, encoding="utf-8")
            stderr_path.write_text(proc.stderr, encoding="utf-8")
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            rc = None
            stdout_path.write_text((exc.stdout or "") if isinstance(exc.stdout, str) else "", encoding="utf-8")
            stderr_path.write_text((exc.stderr or "") if isinstance(exc.stderr, str) else "", encoding="utf-8")
            error = "timeout"
        except OSError as exc:
            rc = None
            stdout_path.write_text("", encoding="utf-8")
            stderr_path.write_text(str(exc), encoding="utf-8")
            error = f"execution_error: {exc}"
        step_ok = not timed_out and error is None and rc in step["accepted_exit_codes"]
        results.append({
            "id": step["id"], "argv": step["argv"], "resolved_executable": step["argv"][0],
            "cwd": step["cwd"], "timeout_seconds": step["timeout_seconds"], "started_at": started,
            "ended_at": _utc(), "duration_seconds": round(time.monotonic() - start, 6), "exit_code": rc,
            "timed_out": timed_out, "ok": step_ok, "error": error,
            "stdout": stdout_path.relative_to(repo).as_posix(), "stderr": stderr_path.relative_to(repo).as_posix(),
            "release_blocking": step["release_blocking"],
        })
        if not step_ok and step["release_blocking"]:
            ok = False
            break
    artifact_check = _verify_artifact(repo / contract["artifact"]["path"], contract) if operation in {"build", "verify", "publish", "adopt", "verify_current"} else None
    if artifact_check is not None and not artifact_check["ok"]:
        ok = False
    preserved_after = _snapshot(repo, contract["preserve"])
    forbidden_after = _snapshot(repo, contract["forbid_mutation"])
    preserve_ok = preserved_before == preserved_after
    forbidden_ok = forbidden_before == forbidden_after
    if not preserve_ok or not forbidden_ok:
        ok = False
    payload = {
        "schema": EVIDENCE_SCHEMA, "schema_version": "1.0", "ok": ok,
        "action": f"release_contract_{operation}", "status": "completed" if ok else "failed",
        "run_id": run_id, "repository": contract["repository"], "operation": operation,
        "steps": results, "artifact": artifact_check,
        "preservation": {"ok": preserve_ok, "before": preserved_before, "after": preserved_after},
        "forbidden_mutation": {"ok": forbidden_ok, "before": forbidden_before, "after": forbidden_after},
        "created_at": _utc(),
    }
    evidence_path = evidence_dir / "evidence.json"
    evidence_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    payload["evidence_path"] = evidence_path.relative_to(repo).as_posix()
    return payload
