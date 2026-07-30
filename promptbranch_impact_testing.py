from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from importlib import metadata
from pathlib import Path
from typing import Any, Iterable

SCHEMA = "promptbranch.test.impact_plan"
SCHEMA_VERSION = "1.0"
DEFAULT_MAP = ".promptbranch/test-impact-map.json"
MODES = ("edit", "component", "candidate")
STRICT_RELEASE_STEPS = (
    "full_direct",
    "full_localhost",
    "live_profile_preflight",
    "live_project_ensure",
    "ask_live",
    "visual_artifact_roundtrip",
    "release_live",
    "import_smoke",
    "artifact_guard",
    "adoption_verification",
)

class ImpactTestingError(ValueError):
    pass


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()




def _git_revision(repo: Path, ref: str) -> str | None:
    proc = subprocess.run(["git", "rev-parse", "--verify", ref], cwd=repo, text=True, capture_output=True, check=False)
    return proc.stdout.strip() if proc.returncode == 0 and proc.stdout.strip() else None


def _path_fingerprint(repo: Path, relative: str) -> dict[str, Any]:
    path = repo / relative
    if not path.exists():
        return {"path": relative, "kind": "missing", "sha256": None}
    if path.is_symlink():
        target = os.readlink(path)
        return {"path": relative, "kind": "symlink", "sha256": _sha256_bytes(target.encode()), "target": target}
    if path.is_file():
        return {"path": relative, "kind": "file", "sha256": _sha256_bytes(path.read_bytes()), "size_bytes": path.stat().st_size}
    return {"path": relative, "kind": "other", "sha256": None}


def _test_definition_fingerprints(repo: Path, commands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    paths: set[str] = set()
    for item in commands:
        for token in item.get("argv") or []:
            candidate = str(token).split("::", 1)[0].replace(os.sep, "/")
            if candidate in {".", ".."} or candidate.startswith("-"):
                continue
            path = repo / candidate
            if path.is_file() and (candidate.startswith("tests/") or candidate.startswith("scripts/") or path.suffix in {".py", ".sh", ".json", ".yml", ".yaml", ".toml"}):
                paths.add(candidate)
    return [_path_fingerprint(repo, path) for path in sorted(paths)]


def _dependency_identity() -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for name in ("pytest", "fastapi", "starlette"):
        try:
            result[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            result[name] = None
    return result


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ImpactTestingError(f"cannot read impact map {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ImpactTestingError("impact map must be a JSON object")
    return payload


def load_impact_map(repo_path: str | Path = ".", map_path: str = DEFAULT_MAP) -> dict[str, Any]:
    repo = Path(repo_path).expanduser().resolve()
    path = (repo / map_path).resolve()
    try:
        path.relative_to(repo)
    except ValueError as exc:
        raise ImpactTestingError("impact map must remain inside the repository") from exc
    payload = _read_json(path)
    required = {"schema", "schema_version", "groups", "rules", "dependencies"}
    unknown = sorted(set(payload) - required)
    missing = sorted(required - set(payload))
    if unknown or missing:
        raise ImpactTestingError(f"impact map keys invalid: missing={missing} unknown={unknown}")
    if payload["schema"] != "promptbranch.test.impact_map" or payload["schema_version"] != "1.0":
        raise ImpactTestingError("unsupported impact map schema identity")
    if not isinstance(payload["groups"], dict) or not payload["groups"]:
        raise ImpactTestingError("impact map groups must be a non-empty object")
    if not isinstance(payload["rules"], list) or not payload["rules"]:
        raise ImpactTestingError("impact map rules must be a non-empty list")
    if not isinstance(payload["dependencies"], dict):
        raise ImpactTestingError("impact map dependencies must be an object")
    for group, spec in payload["groups"].items():
        if not isinstance(group, str) or not group or not isinstance(spec, dict):
            raise ImpactTestingError("impact map group entries are invalid")
        if set(spec) != {"commands", "modes", "transport_independent"}:
            raise ImpactTestingError(f"group {group} must declare commands, modes and transport_independent")
        if not isinstance(spec["commands"], list) or not spec["commands"]:
            raise ImpactTestingError(f"group {group} commands must be non-empty")
        if not all(isinstance(cmd, list) and cmd and all(isinstance(x, str) and x for x in cmd) for cmd in spec["commands"]):
            raise ImpactTestingError(f"group {group} commands must be argv arrays")
        modes = spec["modes"]
        if not isinstance(modes, list) or not modes or any(mode not in MODES for mode in modes):
            raise ImpactTestingError(f"group {group} modes are invalid")
        if not isinstance(spec["transport_independent"], bool):
            raise ImpactTestingError(f"group {group} transport_independent must be boolean")
    known = set(payload["groups"])
    for index, rule in enumerate(payload["rules"]):
        if not isinstance(rule, dict) or set(rule) != {"patterns", "groups", "reason"}:
            raise ImpactTestingError(f"rule {index} must contain patterns, groups and reason")
        if not isinstance(rule["patterns"], list) or not rule["patterns"]:
            raise ImpactTestingError(f"rule {index} patterns must be non-empty")
        if not isinstance(rule["groups"], list) or not rule["groups"]:
            raise ImpactTestingError(f"rule {index} groups must be non-empty")
        unknown_groups = sorted(set(rule["groups"]) - known)
        if unknown_groups:
            raise ImpactTestingError(f"rule {index} references unknown groups {unknown_groups}")
    for group, deps in payload["dependencies"].items():
        if group not in known or not isinstance(deps, list) or set(deps) - known:
            raise ImpactTestingError(f"dependency entry for {group} is invalid")
    payload["_path"] = str(path)
    payload["_sha256"] = _sha256_bytes(path.read_bytes())
    return payload


def changed_files(repo_path: str | Path = ".", base: str = "HEAD") -> list[str]:
    repo = Path(repo_path).expanduser().resolve()
    commands = [
        ["git", "diff", "--name-only", f"{base}...HEAD", "--"],
        ["git", "diff", "--name-only", "--"],
        ["git", "diff", "--name-only", "--cached", "--"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ]
    paths: set[str] = set()
    for command in commands:
        proc = subprocess.run(command, cwd=repo, text=True, capture_output=True, check=False)
        if proc.returncode != 0:
            raise ImpactTestingError(f"git change discovery failed: {' '.join(command)}: {proc.stderr.strip()}")
        for line in proc.stdout.splitlines():
            value = line.strip().replace(os.sep, "/")
            if value:
                paths.add(value)
    return sorted(paths)


def _dependency_closure(selected: Iterable[str], dependencies: dict[str, list[str]]) -> list[str]:
    result = set(selected)
    pending = list(result)
    while pending:
        group = pending.pop()
        for dep in dependencies.get(group, []):
            if dep not in result:
                result.add(dep)
                pending.append(dep)
    return sorted(result)


def _version(repo: Path) -> str:
    path = repo / "VERSION"
    return path.read_text(encoding="utf-8").strip() if path.is_file() else "unknown"


def build_impact_plan(
    repo_path: str | Path = ".",
    *,
    base: str = "HEAD",
    mode: str = "edit",
    map_path: str = DEFAULT_MAP,
    explicit_changed_files: Iterable[str] | None = None,
) -> dict[str, Any]:
    if mode not in MODES:
        raise ImpactTestingError(f"unsupported impact mode {mode!r}")
    repo = Path(repo_path).expanduser().resolve()
    mapping = load_impact_map(repo, map_path)
    changed = sorted(set(explicit_changed_files if explicit_changed_files is not None else changed_files(repo, base)))
    reasons: dict[str, list[dict[str, str]]] = {}
    unmapped: list[str] = []
    directly_selected: set[str] = set()
    for changed_file in changed:
        matches = []
        for rule in mapping["rules"]:
            if any(fnmatch.fnmatchcase(changed_file, pattern) for pattern in rule["patterns"]):
                matches.append(rule)
        if not matches:
            unmapped.append(changed_file)
            continue
        for rule in matches:
            for group in rule["groups"]:
                directly_selected.add(group)
                reasons.setdefault(group, []).append({"file": changed_file, "reason": rule["reason"]})
    selected = _dependency_closure(directly_selected, mapping["dependencies"])
    selected_for_mode = [g for g in selected if mode in mapping["groups"][g]["modes"]]
    for group in selected_for_mode:
        if group not in directly_selected:
            reasons.setdefault(group, []).append({"file": "<dependency>", "reason": "transitive dependency closure"})
    commands = []
    for group in selected_for_mode:
        spec = mapping["groups"][group]
        for argv in spec["commands"]:
            commands.append({
                "group": group,
                "argv": argv,
                "transport_independent": spec["transport_independent"],
            })
    changed_fingerprints = [_path_fingerprint(repo, path) for path in changed]
    test_definition_fingerprints = _test_definition_fingerprints(repo, commands)
    runtime_identity = {
        "python_executable": os.path.abspath(sys.executable),
        "python_prefix": os.path.abspath(sys.prefix),
        "python_version": platform.python_version(),
        "platform_system": platform.system(),
        "platform_release": platform.release(),
        "platform_machine": platform.machine(),
        "dependencies": _dependency_identity(),
    }
    key_material = {
        "version": _version(repo),
        "base": base,
        "base_revision": _git_revision(repo, base),
        "head_revision": _git_revision(repo, "HEAD"),
        "mode": mode,
        "changed_files": changed,
        "changed_fingerprints": changed_fingerprints,
        "selected_groups": selected_for_mode,
        "commands": commands,
        "test_definition_fingerprints": test_definition_fingerprints,
        "map_sha256": mapping["_sha256"],
        "runtime_identity": runtime_identity,
    }
    evidence_key = _sha256_bytes(json.dumps(key_material, sort_keys=True, separators=(",", ":")).encode())
    ok = bool(changed) and bool(selected_for_mode) and not unmapped
    status = "impact_plan_ready" if ok else "impact_plan_blocked"
    errors = []
    if not changed:
        errors.append("no changed files were detected")
    if unmapped:
        errors.append("changed files without deterministic test mapping: " + ", ".join(unmapped))
    if changed and not selected_for_mode:
        errors.append(f"no selected groups support mode {mode}")
    return {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "ok": ok,
        "action": "test_impacted_plan",
        "status": status,
        "repo_path": str(repo),
        "version": _version(repo),
        "base": base,
        "mode": mode,
        "changed_files": changed,
        "unmapped_changed_files": unmapped,
        "directly_selected_groups": sorted(directly_selected),
        "selected_groups": selected_for_mode,
        "selection_reasons": reasons,
        "commands": commands,
        "deferred_strict_release_steps": list(STRICT_RELEASE_STEPS),
        "full_release_validation_required": True,
        "strict_adoption_gate_unchanged": True,
        "map_path": mapping["_path"],
        "map_sha256": mapping["_sha256"],
        "changed_file_fingerprints": changed_fingerprints,
        "test_definition_fingerprints": test_definition_fingerprints,
        "runtime_identity": runtime_identity,
        "base_revision": key_material["base_revision"],
        "head_revision": key_material["head_revision"],
        "evidence_key": evidence_key,
        "errors": errors,
        "safety": {"read_only_plan": True, "project_source_mutated": False, "adoption_performed": False},
    }


def execute_impact_plan(plan: dict[str, Any], *, timeout_seconds: float = 600.0, evidence_dir: str | Path | None = None) -> dict[str, Any]:
    if plan.get("ok") is not True:
        return {**plan, "action": "test_impacted", "status": "impact_execution_refused", "execution": []}
    repo = Path(str(plan["repo_path"])).resolve()
    cache_path = None
    if evidence_dir is not None:
        cache_root = Path(evidence_dir).expanduser().resolve()
        cache_root.mkdir(parents=True, exist_ok=True)
        cache_path = cache_root / f"{plan['evidence_key']}.json"
        if cache_path.is_file():
            cached = _read_json(cache_path)
            if cached.get("ok") is True and cached.get("evidence_key") == plan.get("evidence_key"):
                return {**cached, "status": "reused_impact_evidence", "evidence_reused": True, "cache_path": str(cache_path)}
    started = time.monotonic()
    results = []
    for item in plan["commands"]:
        command = list(item["argv"])
        step_start = time.monotonic()
        try:
            proc = subprocess.run(command, cwd=repo, text=True, capture_output=True, timeout=timeout_seconds, check=False)
            result = {
                **item,
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
                "duration_seconds": round(time.monotonic() - step_start, 3),
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            }
        except subprocess.TimeoutExpired as exc:
            result = {
                **item,
                "ok": False,
                "returncode": 124,
                "duration_seconds": round(time.monotonic() - step_start, 3),
                "stdout": exc.stdout or "",
                "stderr": exc.stderr or "",
                "error": "timeout",
            }
        results.append(result)
        if not result["ok"]:
            break
    ok = len(results) == len(plan["commands"]) and all(item["ok"] for item in results)
    payload = {
        **plan,
        "ok": ok,
        "action": "test_impacted",
        "status": "impacted_tests_passed" if ok else "impacted_tests_failed",
        "execution": results,
        "executed_command_count": len(results),
        "duration_seconds": round(time.monotonic() - started, 3),
        "evidence_reused": False,
    }
    if cache_path is not None and ok:
        cache_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        payload["cache_path"] = str(cache_path)
    return payload


__all__ = [
    "DEFAULT_MAP", "ImpactTestingError", "MODES", "SCHEMA", "SCHEMA_VERSION",
    "build_impact_plan", "changed_files", "execute_impact_plan", "load_impact_map",
]
