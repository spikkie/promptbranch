from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "promptbranch.ai.operational_lifecycle_evidence"
SCHEMA_VERSION = "1.0"
REQUIRED_TOP_LEVEL_STEPS = {
    "full_direct",
    "sandbox_mutation_rollback_gate",
    "full_localhost",
    "live_profile_preflight",
    "live_project_ensure",
    "ask_live",
    "visual_artifact_roundtrip",
    "release_live",
    "import_smoke",
    "artifact_guard",
}

class OperationalEvidenceError(ValueError):
    pass


def _json_from_file(path: str | Path) -> dict[str, Any]:
    candidate = Path(path).expanduser().resolve()
    try:
        raw = candidate.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise OperationalEvidenceError(f"cannot read evidence input {candidate}: {exc}") from exc
    # Accept pure JSON and tee/log wrappers containing one or more JSON objects.
    try:
        value = json.loads(raw)
        if isinstance(value, dict):
            return value
    except Exception:
        pass
    decoder = json.JSONDecoder()
    objects: list[dict[str, Any]] = []
    for index, char in enumerate(raw):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(raw[index:])
        except Exception:
            continue
        if isinstance(value, dict):
            objects.append(value)
    if not objects:
        raise OperationalEvidenceError(f"no JSON object found in {candidate}")
    return objects[-1]


def _norm(value: object) -> str:
    text = str(value or "").strip()
    return text[1:] if text.startswith("v") else text


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_hash(payload: dict[str, Any]) -> str:
    clone = json.loads(json.dumps(payload))
    clone.pop("evidence_sha256", None)
    return hashlib.sha256(json.dumps(clone, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build_operational_lifecycle_evidence(
    *,
    repo_path: str | Path,
    all_tests_summary: str | Path,
    artifact_guard: str | Path,
    adoption_result: str | Path,
    current_result: str | Path,
    source_evidence: str | Path,
    artifact: str | Path,
) -> dict[str, Any]:
    repo = Path(repo_path).expanduser().resolve()
    version = (repo / "VERSION").read_text(encoding="utf-8").strip()
    summary = _json_from_file(all_tests_summary)
    guard = _json_from_file(artifact_guard)
    adoption = _json_from_file(adoption_result)
    current = _json_from_file(current_result)
    source = _json_from_file(source_evidence)
    artifact_path = Path(artifact).expanduser().resolve()
    steps = summary.get("steps") if isinstance(summary.get("steps"), list) else []
    step_by_name = {str(item.get("name")): item for item in steps if isinstance(item, dict) and item.get("name")}
    missing_steps = sorted(REQUIRED_TOP_LEVEL_STEPS - set(step_by_name))
    failed_steps = sorted(name for name, item in step_by_name.items() if name in REQUIRED_TOP_LEVEL_STEPS and item.get("ok") is not True)
    tested = int(summary.get("tested") or len(steps))
    succeeded = int(summary.get("succeeded") or sum(1 for item in steps if item.get("ok") is True))
    failed = int(summary.get("failed") or sum(1 for item in steps if item.get("ok") is not True and item.get("skipped") is not True))
    skipped = int(summary.get("skipped") or sum(1 for item in steps if item.get("skipped") is True))
    summary_green = (
        summary.get("ok") is True
        and summary.get("final_verdict") == "GO"
        and tested == 10 and succeeded == 10 and failed == 0 and skipped == 0
        and not missing_steps and not failed_steps
    )
    source_identity = {
        "requested_filename": source.get("requested_filename"),
        "assigned_filename": source.get("assigned_filename"),
        "processed_file_id": source.get("processed_file_id"),
        "library_metadata_object_id": source.get("library_metadata_object_id"),
        "repo_id": source.get("repo_id"),
    }
    source_checks = source.get("checks") if isinstance(source.get("checks"), dict) else {}
    source_green = bool(
        source.get("ok") is True
        and source.get("status") == "source_evidence_verified"
        and source.get("requested_filename")
        and source.get("assigned_filename")
        and str(source.get("processed_file_id") or "").startswith("file_")
        and str(source.get("library_metadata_object_id") or "").startswith("libfile_")
        and source.get("repo_id")
        and (not source_checks or all(value is True for value in source_checks.values()))
    )

    source_verification = adoption.get("source_verification") if isinstance(adoption.get("source_verification"), dict) else {}
    adoption_project_source_mutated = adoption.get("project_source_mutated")
    if adoption_project_source_mutated is None:
        adoption_project_source_mutated = source_verification.get("project_source_mutated")
    adoption_green = (
        adoption.get("ok") is True
        and adoption.get("status") in {"adopted", "release_adopted_and_verified"}
        and adoption.get("artifact_registry_updated") is True
        and adoption.get("state_artifact_updated") is True
        and adoption.get("state_source_updated") is True
        and adoption.get("source_verified") is True
        and adoption.get("source_evidence_verified") is True
        and adoption_project_source_mutated is False
    )

    current_record = current
    repos = current.get("repos") if isinstance(current.get("repos"), dict) else {}
    source_repo_id = str(source.get("repo_id") or "")
    if repos:
        selected = repos.get(source_repo_id)
        if not isinstance(selected, dict) and len(repos) == 1:
            selected = next(iter(repos.values()))
        if isinstance(selected, dict):
            current_record = selected
    current_runtime = current_record.get("runtime") if isinstance(current_record.get("runtime"), dict) else {}
    current_state = current_record.get("state") if isinstance(current_record.get("state"), dict) else {}
    current_registry = current_record.get("registry_current") if isinstance(current_record.get("registry_current"), dict) else {}
    current_consistency = current_record.get("consistency") if isinstance(current_record.get("consistency"), dict) else {}
    current_version = _norm(
        current_record.get("version")
        or current_record.get("current_version")
        or current_record.get("artifact_version")
        or current_runtime.get("version")
        or current_state.get("artifact_version")
        or current_registry.get("version")
    )
    current_status = str(current_record.get("status") or current.get("status") or "")
    current_green = bool(
        current.get("ok") is True
        and current_record.get("ok", True) is True
        and current_status in {"artifact_registry_loaded", "current", "verified", "release_adopted_and_verified"}
        and current_version == _norm(version)
        and (not current_consistency or all(value is True for value in current_consistency.values() if isinstance(value, bool)))
    )
    guard_green = guard.get("ok") is True and guard.get("status") == "guard_passed" and int(guard.get("failure_count") or 0) == 0
    artifact_green = artifact_path.is_file()
    artifact_sha256 = _sha256_file(artifact_path) if artifact_green else None
    artifact_filename = artifact_path.name
    identity_green = bool(
        artifact_green
        and source_identity["requested_filename"] == artifact_filename
        and adoption.get("requested_source_ref") == source_identity["requested_filename"]
        and adoption.get("assigned_source_ref") == source_identity["assigned_filename"]
        and adoption.get("processed_file_id") == source_identity["processed_file_id"]
        and adoption.get("library_metadata_object_id") == source_identity["library_metadata_object_id"]
        and adoption.get("repo_id") == source_identity["repo_id"]
        and (not current_registry or current_registry.get("filename") == artifact_filename)
        and (not current_registry or current_registry.get("sha256") == artifact_sha256)
        and (not current_state or current_state.get("source_ref") == source_identity["assigned_filename"])
    )
    correction_step = step_by_name.get("full_direct", {})
    recovery_step = step_by_name.get("full_localhost", {})
    operational = {
        "correction_verified": correction_step.get("ok") is True,
        "lifecycle_verified": summary_green,
        "publication_verified": source_green,
        "adoption_verified": adoption_green and current_green,
        "accepted_current_verified": current_green,
        "recovery_verified": recovery_step.get("ok") is True and step_by_name.get("artifact_guard", {}).get("ok") is True,
        "rollback_gate_verified": step_by_name.get("sandbox_mutation_rollback_gate", {}).get("ok") is True,
    }
    errors = []
    checks = {
        "summary": summary_green,
        "artifact_guard": guard_green,
        "artifact": artifact_green,
        "source_identity": source_green,
        "adoption": adoption_green,
        "accepted_current": current_green,
        "identity_binding": identity_green,
        "operational_dimensions": all(operational.values()),
    }
    for name, ok in checks.items():
        if not ok:
            errors.append(f"operational evidence check failed: {name}")
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "ok": not errors,
        "action": "application_architecture_operational_evidence",
        "status": "operational_evidence_verified" if not errors else "operational_evidence_invalid",
        "proven_level": "operational" if not errors else "executable",
        "application_id": "promptbranch",
        "version": version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "repo_path": str(repo),
        "artifact": {
            "path": str(artifact_path),
            "filename": artifact_path.name,
            "sha256": artifact_sha256,
            "size_bytes": artifact_path.stat().st_size if artifact_green else None,
        },
        "release_summary": {
            "tested": tested,
            "succeeded": succeeded,
            "failed": failed,
            "skipped": skipped,
            "final_verdict": summary.get("final_verdict"),
            "missing_required_steps": missing_steps,
            "failed_required_steps": failed_steps,
        },
        "project_source": source_identity,
        "adoption": {
            "status": adoption.get("status"),
            "source_verified": adoption.get("source_verified"),
            "source_evidence_verified": adoption.get("source_evidence_verified"),
            "artifact_registry_updated": adoption.get("artifact_registry_updated"),
            "state_artifact_updated": adoption.get("state_artifact_updated"),
            "state_source_updated": adoption.get("state_source_updated"),
            "project_source_mutated": adoption_project_source_mutated,
        },
        "accepted_current": {
            "status": current_status,
            "version": current_version,
            "repo_id": current_record.get("repo_id") or source_repo_id,
            "artifact_filename": current_registry.get("filename"),
            "artifact_sha256": current_registry.get("sha256"),
            "source_ref": current_state.get("source_ref"),
        },
        "operational_dimensions": operational,
        "input_paths": {
            "all_tests_summary": str(Path(all_tests_summary).expanduser().resolve()),
            "artifact_guard": str(Path(artifact_guard).expanduser().resolve()),
            "adoption_result": str(Path(adoption_result).expanduser().resolve()),
            "current_result": str(Path(current_result).expanduser().resolve()),
            "source_evidence": str(Path(source_evidence).expanduser().resolve()),
        },
        "checks": checks,
        "errors": errors,
        "safety": {
            "read_only_validation": True,
            "project_source_mutated": False,
            "adoption_performed_by_builder": False,
            "state_mutated_by_builder": False,
        },
    }
    payload["evidence_sha256"] = _canonical_hash(payload)
    return payload


def validate_operational_lifecycle_evidence(
    evidence: str | Path | dict[str, Any], *, repo_path: str | Path = "."
) -> dict[str, Any]:
    payload = _json_from_file(evidence) if not isinstance(evidence, dict) else json.loads(json.dumps(evidence))
    repo = Path(repo_path).expanduser().resolve()
    expected_version = (repo / "VERSION").read_text(encoding="utf-8").strip()
    errors = []
    required = {
        "schema", "schema_version", "ok", "status", "proven_level", "application_id",
        "version", "artifact", "release_summary", "project_source", "adoption",
        "accepted_current", "operational_dimensions", "checks", "errors", "safety", "evidence_sha256",
    }
    missing = sorted(required - set(payload))
    if missing:
        errors.append(f"missing required fields: {missing}")
    if payload.get("schema") != SCHEMA or payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("unsupported operational evidence schema identity")
    if _norm(payload.get("version")) != _norm(expected_version):
        errors.append(f"evidence version {payload.get('version')!r} does not match repository {expected_version!r}")
    if payload.get("application_id") != "promptbranch":
        errors.append("operational evidence application_id must be promptbranch")
    if payload.get("evidence_sha256") != _canonical_hash(payload):
        errors.append("operational evidence canonical hash mismatch")
    dimensions = payload.get("operational_dimensions") if isinstance(payload.get("operational_dimensions"), dict) else {}
    expected_dimensions = {
        "correction_verified", "lifecycle_verified", "publication_verified", "adoption_verified",
        "accepted_current_verified", "recovery_verified", "rollback_gate_verified",
    }
    if set(dimensions) != expected_dimensions or not all(value is True for value in dimensions.values()):
        errors.append("all operational dimensions must be present and true")
    safety = payload.get("safety") if isinstance(payload.get("safety"), dict) else {}
    if safety.get("read_only_validation") is not True or safety.get("project_source_mutated") is not False:
        errors.append("operational evidence safety contract is invalid")
    ok = not errors and payload.get("ok") is True and payload.get("status") == "operational_evidence_verified"
    return {
        "ok": ok,
        "action": "application_architecture_operational_validate",
        "status": "operational_validated" if ok else "operational_invalid",
        "proven_level": "operational" if ok else "executable",
        "requested_level": "operational",
        "max_supported_level": "operational",
        "repo_path": str(repo),
        "evidence": payload,
        "error_count": len(errors),
        "errors": errors,
        "safety": {"read_only": True, "state_mutated": False, "project_source_mutated": False},
    }


__all__ = [
    "OperationalEvidenceError", "SCHEMA", "SCHEMA_VERSION",
    "build_operational_lifecycle_evidence", "validate_operational_lifecycle_evidence",
]
