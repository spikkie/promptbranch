from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

SCHEMA = "promptbranch.application.change"
SCHEMA_VERSION = "1.0"
MAX_OPERATION_CONTENT_BYTES = 256 * 1024
MAX_TOTAL_CONTENT_BYTES = 1024 * 1024
DEFAULT_CONFIG = "examples/application-pilot/k8s-game-mvp.change.json"
EVIDENCE_SCHEMA = "promptbranch.application.change.evidence"
EVIDENCE_SCHEMA_VERSION = "1.0"


class ApplicationChangeError(ValueError):
    """Raised when controlled external-application change execution is unsafe or invalid."""


def _object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ApplicationChangeError(f"{label} must be an object")
    return value


def _exact_keys(value: dict[str, Any], required: Iterable[str], label: str) -> None:
    expected = set(required)
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing:
        raise ApplicationChangeError(f"{label} missing required fields: {', '.join(missing)}")
    if unknown:
        raise ApplicationChangeError(f"{label} contains unknown fields: {', '.join(unknown)}")


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ApplicationChangeError(f"{label} must be a non-empty string")
    return value.strip()


def _relative(value: object, label: str) -> str:
    text = _text(value, label)
    if "\\" in text:
        raise ApplicationChangeError(f"{label} must use forward slashes")
    path = Path(text)
    if path.is_absolute() or ".." in path.parts or text == ".":
        raise ApplicationChangeError(f"{label} must be a repository-relative path without traversal")
    if path.parts and path.parts[0] == ".git":
        raise ApplicationChangeError(f"{label} may not target .git")
    return path.as_posix()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_target_path(target: Path, relative: str) -> Path:
    rel = Path(_relative(relative, "operation.path"))
    current = target
    for part in rel.parts[:-1]:
        current = current / part
        if current.exists() and current.is_symlink():
            raise ApplicationChangeError(f"operation path crosses symlink: {relative}")
        if current.exists() and not current.is_dir():
            raise ApplicationChangeError(f"operation parent is not a directory: {relative}")
    path = target / rel
    if path.exists() and path.is_symlink():
        raise ApplicationChangeError(f"operation path is a symlink: {relative}")
    try:
        path.parent.resolve().relative_to(target.resolve())
    except ValueError as exc:
        raise ApplicationChangeError(f"operation path escapes target repository: {relative}") from exc
    return path


def _snapshot(path: Path, relative: str) -> dict[str, Any]:
    if not path.exists():
        return {"path": relative, "state": "absent", "sha256": None, "size_bytes": 0, "mode": None}
    if not path.is_file():
        raise ApplicationChangeError(f"operation target must be a regular file or absent: {relative}")
    mode = stat.S_IMODE(path.stat().st_mode)
    return {
        "path": relative,
        "state": "file",
        "sha256": _sha256_file(path),
        "size_bytes": path.stat().st_size,
        "mode": mode,
    }


def _atomic_write(path: Path, data: bytes, *, mode: int = 0o644) -> list[str]:
    created_dirs: list[str] = []
    missing: list[Path] = []
    parent = path.parent
    while not parent.exists():
        missing.append(parent)
        parent = parent.parent
    for directory in reversed(missing):
        directory.mkdir()
        created_dirs.append(str(directory))
    fd, temp_name = tempfile.mkstemp(prefix=".promptbranch-change-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, mode)
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
    return created_dirs


def validate_application_change_definition(payload: object, *, config_path: str = DEFAULT_CONFIG) -> dict[str, Any]:
    root = _object(payload, "change definition")
    required = {"schema", "schema_version", "change", "target", "authorization", "operations", "rollback", "authority"}
    _exact_keys(root, required, "change definition")
    if root["schema"] != SCHEMA or root["schema_version"] != SCHEMA_VERSION:
        raise ApplicationChangeError("unsupported application change schema or schema_version")

    change = _object(root["change"], "change")
    _exact_keys(change, {"id", "pilot_id", "application_repo_id", "summary"}, "change")
    normalized_change = {key: _text(change[key], f"change.{key}") for key in change}

    target = _object(root["target"], "target")
    _exact_keys(target, {"required_repo_marker"}, "target")
    marker = _text(target["required_repo_marker"], "target.required_repo_marker")
    if marker != ".git":
        raise ApplicationChangeError("target.required_repo_marker must be .git")
    normalized_target = {"required_repo_marker": marker}

    authorization = _object(root["authorization"], "authorization")
    _exact_keys(authorization, {"mode", "execute_flag_required", "exact_change_id_required"}, "authorization")
    if authorization["mode"] != "explicit_cli_exact_change_id":
        raise ApplicationChangeError("authorization.mode must be explicit_cli_exact_change_id")
    if authorization["execute_flag_required"] is not True or authorization["exact_change_id_required"] is not True:
        raise ApplicationChangeError("controlled change execution requires --execute and exact change-id authorization")

    operations_raw = root["operations"]
    if not isinstance(operations_raw, list) or not operations_raw:
        raise ApplicationChangeError("operations must be a non-empty array")
    if len(operations_raw) > 32:
        raise ApplicationChangeError("operations exceeds bounded maximum of 32")
    operations: list[dict[str, Any]] = []
    ids: set[str] = set()
    paths: set[str] = set()
    for index, raw in enumerate(operations_raw):
        operation = _object(raw, f"operations[{index}]")
        _exact_keys(operation, {"id", "action", "path", "precondition", "content"}, f"operations[{index}]")
        operation_id = _text(operation["id"], f"operations[{index}].id")
        if operation_id in ids:
            raise ApplicationChangeError("operation ids must be unique")
        ids.add(operation_id)
        if operation["action"] != "write_file":
            raise ApplicationChangeError(f"operations[{index}].action must be write_file")
        relative = _relative(operation["path"], f"operations[{index}].path")
        if relative in paths:
            raise ApplicationChangeError("operation paths must be unique")
        paths.add(relative)
        precondition = _object(operation["precondition"], f"operations[{index}].precondition")
        state = precondition.get("state")
        if state == "absent":
            _exact_keys(precondition, {"state"}, f"operations[{index}].precondition")
            normalized_precondition = {"state": "absent", "sha256": None}
        elif state == "exact_sha256":
            _exact_keys(precondition, {"state", "sha256"}, f"operations[{index}].precondition")
            expected = _text(precondition["sha256"], f"operations[{index}].precondition.sha256").lower()
            if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
                raise ApplicationChangeError(f"operations[{index}].precondition.sha256 must be lowercase SHA-256 hex")
            normalized_precondition = {"state": "exact_sha256", "sha256": expected}
        else:
            raise ApplicationChangeError(f"operations[{index}].precondition.state must be absent or exact_sha256")
        content = operation["content"]
        if not isinstance(content, str):
            raise ApplicationChangeError(f"operations[{index}].content must be a string")
        content_bytes = content.encode("utf-8")
        if len(content_bytes) > MAX_OPERATION_CONTENT_BYTES:
            raise ApplicationChangeError(f"operations[{index}].content exceeds bounded size limit")
        operations.append(
            {
                "id": operation_id,
                "action": "write_file",
                "path": relative,
                "precondition": normalized_precondition,
                "content": content,
                "expected_after_sha256": _sha256_bytes(content_bytes),
                "expected_after_size_bytes": len(content_bytes),
            }
        )

    if sum(item["expected_after_size_bytes"] for item in operations) > MAX_TOTAL_CONTENT_BYTES:
        raise ApplicationChangeError("operations exceed bounded total content size limit")

    rollback = _object(root["rollback"], "rollback")
    _exact_keys(rollback, {"required", "method", "evidence_location", "reject_post_apply_drift"}, "rollback")
    if rollback["required"] is not True:
        raise ApplicationChangeError("rollback.required must be true")
    if rollback["method"] != "restore_exact_pre_state_bytes":
        raise ApplicationChangeError("rollback.method must be restore_exact_pre_state_bytes")
    if rollback["evidence_location"] != "control_repo_operator_state":
        raise ApplicationChangeError("rollback.evidence_location must be control_repo_operator_state")
    if rollback["reject_post_apply_drift"] is not True:
        raise ApplicationChangeError("rollback.reject_post_apply_drift must be true")

    authority = _object(root["authority"], "authority")
    authority_fields = {
        "target_file_mutation_allowed",
        "git_commands_allowed",
        "git_publication_allowed",
        "project_source_mutation_allowed",
        "deployment_allowed",
        "artifact_adoption_allowed",
        "application_test_execution_allowed",
    }
    _exact_keys(authority, authority_fields, "authority")
    for field in authority_fields:
        if not isinstance(authority[field], bool):
            raise ApplicationChangeError(f"authority.{field} must be boolean")
    required_values = {
        "target_file_mutation_allowed": True,
        "git_commands_allowed": False,
        "git_publication_allowed": False,
        "project_source_mutation_allowed": False,
        "deployment_allowed": False,
        "artifact_adoption_allowed": False,
        "application_test_execution_allowed": False,
    }
    for field, expected in required_values.items():
        if authority[field] is not expected:
            raise ApplicationChangeError(f"authority.{field} must be {str(expected).lower()} for this slice")

    return {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "config_path": config_path,
        "change": normalized_change,
        "target": normalized_target,
        "authorization": dict(authorization),
        "operations": operations,
        "rollback": dict(rollback),
        "authority": dict(authority),
    }


def load_application_change_definition(control_repo: str | Path = ".", config: str = DEFAULT_CONFIG) -> dict[str, Any]:
    root = Path(control_repo).expanduser().resolve()
    config_rel = _relative(config, "config")
    path = root / config_rel
    if not path.is_file():
        raise ApplicationChangeError(f"application change definition not found: {config_rel}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ApplicationChangeError(f"invalid application change definition: {exc}") from exc
    return validate_application_change_definition(payload, config_path=config_rel)


def _bind_target(control: Path, target: Path, definition: dict[str, Any]) -> None:
    if target == control:
        raise ApplicationChangeError("external application repository must be separate from the Promptbranch control repository")
    if not target.is_dir():
        raise ApplicationChangeError(f"external application repository directory does not exist: {target}")
    marker_rel = definition["target"]["required_repo_marker"]
    if not (target / marker_rel).exists():
        raise ApplicationChangeError(
            f"external application repository is not established: required marker missing: {marker_rel}"
        )


def _planned_created_dirs(target: Path, operations: list[dict[str, Any]]) -> list[str]:
    planned: set[str] = set()
    for operation in operations:
        path = _safe_target_path(target, operation["path"])
        parent = path.parent
        while parent != target and not parent.exists():
            planned.add(str(parent))
            parent = parent.parent
    return sorted(planned, key=lambda value: (len(Path(value).parts), value))


def _preflight_operations(target: Path, operations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    snapshots: list[dict[str, Any]] = []
    for operation in operations:
        path = _safe_target_path(target, operation["path"])
        before = _snapshot(path, operation["path"])
        precondition = operation["precondition"]
        if precondition["state"] == "absent" and before["state"] != "absent":
            raise ApplicationChangeError(f"precondition failed for {operation['path']}: expected absent")
        if precondition["state"] == "exact_sha256":
            if before["state"] != "file" or before["sha256"] != precondition["sha256"]:
                raise ApplicationChangeError(f"precondition failed for {operation['path']}: exact SHA-256 mismatch")
        snapshots.append(before)
    return snapshots


def build_application_change_plan(
    control_repo: str | Path,
    target_repo: str | Path,
    config: str = DEFAULT_CONFIG,
) -> dict[str, Any]:
    control = Path(control_repo).expanduser().resolve()
    target = Path(target_repo).expanduser().resolve()
    definition = load_application_change_definition(control, config)
    _bind_target(control, target, definition)
    snapshots = _preflight_operations(target, definition["operations"])
    return {
        "ok": True,
        "action": "application_change_plan",
        "status": "controlled_change_plan_ready",
        "control_repo": str(control),
        "target_repo": str(target),
        "change": definition["change"],
        "authorization": {
            "required": True,
            "mode": definition["authorization"]["mode"],
            "required_change_id": definition["change"]["id"],
            "execute_flag_required": True,
        },
        "operations": [
            {
                "id": operation["id"],
                "action": operation["action"],
                "path": operation["path"],
                "precondition": operation["precondition"],
                "before": snapshots[index],
                "expected_after_sha256": operation["expected_after_sha256"],
                "expected_after_size_bytes": operation["expected_after_size_bytes"],
            }
            for index, operation in enumerate(definition["operations"])
        ],
        "rollback": definition["rollback"],
        "authority": definition["authority"],
        "safety": {
            "read_only": True,
            "target_repo_mutated": False,
            "git_commands_executed": False,
            "git_publication_performed": False,
            "project_source_mutated": False,
            "deployment_performed": False,
            "artifact_adopted": False,
            "application_tests_executed": False,
        },
        "next_authorized_action": "application_change_apply_with_explicit_human_authorization",
    }


def _evidence_root(control: Path, change_id: str, attempt_id: str) -> Path:
    return control / ".pb_profile" / "application_change_evidence" / change_id / attempt_id


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def _capture_before_bytes(evidence_root: Path, target: Path, snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    captured: list[dict[str, Any]] = []
    before_dir = evidence_root / "before"
    before_dir.mkdir(parents=True, exist_ok=True)
    for index, snapshot in enumerate(snapshots):
        item = dict(snapshot)
        if snapshot["state"] == "file":
            source = target / snapshot["path"]
            name = f"{index:03d}.bin"
            destination = before_dir / name
            destination.write_bytes(source.read_bytes())
            item["snapshot_file"] = f"before/{name}"
            if _sha256_file(destination) != snapshot["sha256"]:
                raise ApplicationChangeError(f"failed to verify before snapshot for {snapshot['path']}")
        else:
            item["snapshot_file"] = None
        captured.append(item)
    return captured


def _restore_from_evidence(target: Path, evidence_root: Path, before: list[dict[str, Any]], created_dirs: list[str]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    for snapshot in reversed(before):
        relative = snapshot["path"]
        path = _safe_target_path(target, relative)
        try:
            if snapshot["state"] == "absent":
                if path.exists():
                    if not path.is_file():
                        raise ApplicationChangeError(f"rollback target is not a regular file: {relative}")
                    path.unlink()
            else:
                snapshot_file = evidence_root / str(snapshot["snapshot_file"])
                data = snapshot_file.read_bytes()
                if _sha256_bytes(data) != snapshot["sha256"]:
                    raise ApplicationChangeError(f"rollback snapshot SHA-256 mismatch: {relative}")
                _atomic_write(path, data, mode=int(snapshot["mode"]))
            after = _snapshot(path, relative)
            restored = (
                after["state"] == snapshot["state"]
                and after["sha256"] == snapshot["sha256"]
                and after["size_bytes"] == snapshot["size_bytes"]
            )
            if not restored:
                raise ApplicationChangeError(f"rollback verification mismatch: {relative}")
            results.append({"path": relative, "restored": True, "snapshot": after})
        except Exception as exc:  # rollback must collect all bounded failures
            errors.append(f"{relative}: {exc}")
            results.append({"path": relative, "restored": False, "error": str(exc)})
    for directory_text in sorted(set(created_dirs), key=lambda value: len(Path(value).parts), reverse=True):
        directory = Path(directory_text)
        try:
            directory.relative_to(target)
        except ValueError:
            continue
        try:
            directory.rmdir()
        except (FileNotFoundError, OSError):
            pass
    return {"attempted": True, "succeeded": not errors, "results": results, "errors": errors}


def execute_application_change(
    control_repo: str | Path,
    target_repo: str | Path,
    *,
    config: str = DEFAULT_CONFIG,
    execute: bool = False,
    authorized_change_id: str | None = None,
) -> dict[str, Any]:
    control = Path(control_repo).expanduser().resolve()
    target = Path(target_repo).expanduser().resolve()
    definition = load_application_change_definition(control, config)
    _bind_target(control, target, definition)
    change_id = definition["change"]["id"]
    if not execute:
        raise ApplicationChangeError("controlled application change requires explicit --execute")
    if authorized_change_id != change_id:
        raise ApplicationChangeError(f"controlled application change requires --authorize-change {change_id}")

    snapshots = _preflight_operations(target, definition["operations"])
    attempt_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid4().hex[:12]
    evidence_root = _evidence_root(control, change_id, attempt_id)
    captured_before = _capture_before_bytes(evidence_root, target, snapshots)
    planned_created_dirs = _planned_created_dirs(target, definition["operations"])
    created_dirs: list[str] = list(planned_created_dirs)
    evidence: dict[str, Any] = {
        "schema": EVIDENCE_SCHEMA,
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "status": "before_snapshot_captured",
        "attempt_id": attempt_id,
        "change_id": change_id,
        "pilot_id": definition["change"]["pilot_id"],
        "application_repo_id": definition["change"]["application_repo_id"],
        "control_repo": str(control),
        "target_repo": str(target),
        "authorization": {"execute": True, "authorized_change_id": authorized_change_id, "exact_match": True},
        "before": captured_before,
        "after": [],
        "created_dirs": planned_created_dirs,
        "rollback": {"required": True, "attempted": False, "succeeded": None},
        "safety": {
            "git_commands_executed": False,
            "git_publication_performed": False,
            "project_source_mutated": False,
            "deployment_performed": False,
            "artifact_adopted": False,
            "application_tests_executed": False,
        },
    }
    evidence_path = evidence_root / "evidence.json"
    _write_json(evidence_path, evidence)

    try:
        after_items: list[dict[str, Any]] = []
        for operation in definition["operations"]:
            path = _safe_target_path(target, operation["path"])
            data = operation["content"].encode("utf-8")
            _atomic_write(path, data)
            after = _snapshot(path, operation["path"])
            if after["sha256"] != operation["expected_after_sha256"] or after["size_bytes"] != operation["expected_after_size_bytes"]:
                raise ApplicationChangeError(f"post-write verification failed: {operation['path']}")
            after_items.append({"id": operation["id"], **after})
        evidence["status"] = "applied_and_verified"
        evidence["after"] = after_items
        evidence["created_dirs"] = sorted(set(created_dirs))
        evidence["rollback"] = {"required": True, "attempted": False, "succeeded": None}
        _write_json(evidence_path, evidence)
        return {
            "ok": True,
            "action": "application_change_apply",
            "status": "controlled_change_applied_and_verified",
            "change_id": change_id,
            "target_repo": str(target),
            "evidence_path": str(evidence_path),
            "operation_count": len(definition["operations"]),
            "before": captured_before,
            "after": after_items,
            "rollback": {"available": True, "required_on_failure": True, "evidence_path": str(evidence_path)},
            "safety": {**evidence["safety"], "target_repo_mutated": True, "human_authorization_verified": True},
            "next_authorized_capability": "application_test_diagnosis_and_bounded_correction_loop",
        }
    except Exception as exc:
        rollback = _restore_from_evidence(target, evidence_root, captured_before, created_dirs)
        evidence["status"] = "apply_failed_rollback_verified" if rollback["succeeded"] else "apply_failed_rollback_incomplete"
        evidence["created_dirs"] = sorted(set(created_dirs))
        evidence["rollback"] = rollback
        evidence["failure"] = str(exc)
        _write_json(evidence_path, evidence)
        raise ApplicationChangeError(
            f"application change failed; automatic rollback {'succeeded' if rollback['succeeded'] else 'failed'}: {exc}; evidence={evidence_path}"
        ) from exc


def rollback_application_change(
    target_repo: str | Path,
    evidence_path: str | Path,
    *,
    execute: bool = False,
    authorized_change_id: str | None = None,
) -> dict[str, Any]:
    target = Path(target_repo).expanduser().resolve()
    path = Path(evidence_path).expanduser().resolve()
    if not path.is_file():
        raise ApplicationChangeError(f"application change evidence not found: {path}")
    try:
        evidence = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ApplicationChangeError(f"invalid application change evidence: {exc}") from exc
    if evidence.get("schema") != EVIDENCE_SCHEMA or evidence.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
        raise ApplicationChangeError("unsupported application change evidence schema")
    change_id = _text(evidence.get("change_id"), "evidence.change_id")
    if not execute:
        raise ApplicationChangeError("application change rollback requires explicit --execute")
    if authorized_change_id != change_id:
        raise ApplicationChangeError(f"application change rollback requires --authorize-change {change_id}")
    if str(target) != evidence.get("target_repo"):
        raise ApplicationChangeError("rollback target repository does not match evidence target")
    if evidence.get("status") != "applied_and_verified":
        raise ApplicationChangeError("explicit rollback requires applied_and_verified evidence")

    after_items = evidence.get("after") if isinstance(evidence.get("after"), list) else []
    for item in after_items:
        relative = _relative(item.get("path"), "evidence.after.path")
        current = _snapshot(_safe_target_path(target, relative), relative)
        if current["state"] != "file" or current["sha256"] != item.get("sha256") or current["size_bytes"] != item.get("size_bytes"):
            raise ApplicationChangeError(f"post-apply drift detected; refusing rollback over changed file: {relative}")

    evidence_root = path.parent
    before = evidence.get("before") if isinstance(evidence.get("before"), list) else []
    created_dirs = evidence.get("created_dirs") if isinstance(evidence.get("created_dirs"), list) else []
    rollback = _restore_from_evidence(target, evidence_root, before, [str(item) for item in created_dirs])
    evidence["status"] = "rolled_back_and_verified" if rollback["succeeded"] else "rollback_incomplete"
    evidence["rollback"] = rollback
    _write_json(path, evidence)
    if not rollback["succeeded"]:
        raise ApplicationChangeError(f"application change rollback incomplete; evidence={path}")
    return {
        "ok": True,
        "action": "application_change_rollback",
        "status": "controlled_change_rolled_back_and_verified",
        "change_id": change_id,
        "target_repo": str(target),
        "evidence_path": str(path),
        "rollback": rollback,
        "safety": {
            "target_repo_mutated": True,
            "human_authorization_verified": True,
            "git_commands_executed": False,
            "git_publication_performed": False,
            "project_source_mutated": False,
            "deployment_performed": False,
            "artifact_adopted": False,
            "application_tests_executed": False,
        },
    }
