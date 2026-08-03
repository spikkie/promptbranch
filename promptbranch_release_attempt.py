from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

CHECKPOINT_SCHEMA = "promptbranch.release_control.checkpoint"
CHECKPOINT_SCHEMA_VERSION = "1.0"


class ReleaseAttemptError(RuntimeError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: str | Path) -> str:
    candidate = Path(path)
    digest = hashlib.sha256()
    with candidate.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _zip_entry_count(path: Path) -> int:
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise ReleaseAttemptError(f"ZIP CRC failure at {bad}")
        return len(archive.infolist())


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY)
        except OSError:
            directory_fd = None
        if directory_fd is not None:
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except Exception as exc:  # pragma: no cover - defensive boundary
        raise ReleaseAttemptError(f"checkpoint is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ReleaseAttemptError("checkpoint root must be an object")
    return value


def _extract_json_objects(path: Path) -> list[dict[str, Any]]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    decoder = json.JSONDecoder()
    objects: list[dict[str, Any]] = []
    for index, char in enumerate(raw):
        if char != "{":
            continue
        try:
            value, _end = decoder.raw_decode(raw[index:])
        except Exception:
            continue
        if isinstance(value, dict):
            objects.append(value)
    return objects


def _source_payload(path: Path) -> dict[str, Any]:
    candidates = [
        value
        for value in _extract_json_objects(path)
        if value.get("ok") is True
        and value.get("action") == "add"
        and value.get("persistence_verified") is True
    ]
    if not candidates:
        raise ReleaseAttemptError("Project Source log has no authoritative persistent add result")
    return candidates[-1]


def _project_identity(project_url: str) -> tuple[str, str]:
    parts = [part for part in urlparse(project_url).path.split("/") if part]
    if len(parts) >= 2 and parts[0] == "g":
        project_id = parts[1]
        return project_id, f"https://chatgpt.com/g/{project_id}/project"
    return "", ""


def _candidate_binding(
    *,
    repo_id: str,
    version: str,
    artifact_path: Path,
    git_commit: str,
    contract_sha256: str,
) -> dict[str, Any]:
    if not artifact_path.is_file():
        raise ReleaseAttemptError(f"canonical artifact missing: {artifact_path}")
    artifact_sha = sha256_file(artifact_path)
    return {
        "repo_id": repo_id,
        "version": version,
        "artifact": {
            "filename": artifact_path.name,
            "sha256": artifact_sha,
            "size_bytes": artifact_path.stat().st_size,
            "file_count": _zip_entry_count(artifact_path),
        },
        "git_commit": git_commit,
        "contract_sha256": contract_sha256,
    }


def _new_checkpoint(binding: dict[str, Any]) -> dict[str, Any]:
    now = _utc_now()
    return {
        "schema": CHECKPOINT_SCHEMA,
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "action": "release_control_checkpoint",
        "status": "canonical_artifact_bound",
        "created_at": now,
        "updated_at": now,
        "repo_id": binding["repo_id"],
        "version": binding["version"],
        "artifact": binding["artifact"],
        "evidence_binding": {
            "artifact_sha256": binding["artifact"]["sha256"],
            "git_commit": binding["git_commit"],
            "contract_sha256": binding["contract_sha256"],
        },
        "phase_results": [
            {
                "phase": "canonical-build",
                "ok": True,
                "status": "canonical_artifact_bound",
                "artifact_sha256": binding["artifact"]["sha256"],
                "git_commit": binding["git_commit"],
                "contract_sha256": binding["contract_sha256"],
                "recorded_at": now,
            }
        ],
        "source": None,
        "adoption": None,
    }


def _validate_checkpoint_shape(checkpoint: dict[str, Any]) -> None:
    if checkpoint.get("schema") != CHECKPOINT_SCHEMA:
        raise ReleaseAttemptError("checkpoint schema mismatch")
    if checkpoint.get("schema_version") != CHECKPOINT_SCHEMA_VERSION:
        raise ReleaseAttemptError("checkpoint schema version unsupported")
    if checkpoint.get("action") != "release_control_checkpoint":
        raise ReleaseAttemptError("checkpoint action mismatch")


def _binding_mismatches(checkpoint: dict[str, Any], binding: dict[str, Any]) -> dict[str, dict[str, Any]]:
    evidence = checkpoint.get("evidence_binding") if isinstance(checkpoint.get("evidence_binding"), dict) else {}
    artifact = checkpoint.get("artifact") if isinstance(checkpoint.get("artifact"), dict) else {}
    expected = {
        "repo_id": checkpoint.get("repo_id"),
        "version": checkpoint.get("version"),
        "artifact_filename": artifact.get("filename"),
        "artifact_sha256": artifact.get("sha256") or evidence.get("artifact_sha256"),
        "git_commit": evidence.get("git_commit"),
        "contract_sha256": evidence.get("contract_sha256"),
    }
    actual = {
        "repo_id": binding["repo_id"],
        "version": binding["version"],
        "artifact_filename": binding["artifact"]["filename"],
        "artifact_sha256": binding["artifact"]["sha256"],
        "git_commit": binding["git_commit"],
        "contract_sha256": binding["contract_sha256"],
    }
    return {
        key: {"expected": expected[key], "actual": actual[key]}
        for key in expected
        if str(expected[key] or "") != str(actual[key] or "")
    }


def preflight_checkpoint(
    checkpoint_path: str | Path,
    *,
    repo_id: str,
    version: str,
    artifact_path: str | Path,
    git_commit: str,
    contract_sha256: str,
    source_log_path: str | Path | None = None,
) -> tuple[dict[str, Any], int]:
    checkpoint_file = Path(checkpoint_path)
    artifact = Path(artifact_path)
    binding = _candidate_binding(
        repo_id=repo_id,
        version=version,
        artifact_path=artifact,
        git_commit=git_commit,
        contract_sha256=contract_sha256,
    )
    if not checkpoint_file.exists():
        checkpoint = _new_checkpoint(binding)
        _atomic_write_json(checkpoint_file, checkpoint)
        return {
            "ok": True,
            "action": "release_control_checkpoint_import",
            "status": "new_release_attempt_bound",
            "resume": False,
            "reuse_project_source": False,
            "checkpoint_path": str(checkpoint_file),
            "artifact": binding["artifact"],
            "git_commit": git_commit,
            "contract_sha256": contract_sha256,
            "state_mutated": True,
        }, 0

    try:
        checkpoint = _read_json(checkpoint_file)
        _validate_checkpoint_shape(checkpoint)
    except ReleaseAttemptError as exc:
        return {
            "ok": False,
            "action": "release_control_checkpoint_import",
            "status": "release_attempt_checkpoint_invalid",
            "error": str(exc),
            "checkpoint_path": str(checkpoint_file),
            "state_mutated": False,
        }, 2

    mismatches = _binding_mismatches(checkpoint, binding)
    if mismatches:
        status = (
            "provisional_release_identity_conflict"
            if "artifact_sha256" in mismatches
            else "release_attempt_binding_conflict"
        )
        return {
            "ok": False,
            "action": "release_control_checkpoint_import",
            "status": status,
            "checkpoint_path": str(checkpoint_file),
            "mismatches": mismatches,
            "artifact": binding["artifact"],
            "state_mutated": False,
        }, 2

    source = checkpoint.get("source") if isinstance(checkpoint.get("source"), dict) else None
    if not source:
        return {
            "ok": True,
            "action": "release_control_checkpoint_import",
            "status": "release_attempt_resumed_before_publication",
            "resume": True,
            "reuse_project_source": False,
            "checkpoint_path": str(checkpoint_file),
            "artifact": binding["artifact"],
            "git_commit": git_commit,
            "contract_sha256": contract_sha256,
            "state_mutated": False,
        }, 0

    required = (
        "requested_filename",
        "assigned_filename",
        "processed_file_id",
        "library_metadata_object_id",
        "project_id",
        "project_url",
        "local_sha256",
    )
    missing = [field for field in required if not str(source.get(field) or "").strip()]
    if source.get("persistence_verified") is not True:
        missing.append("persistence_verified")
    if str(source.get("local_sha256") or "").lower() != binding["artifact"]["sha256"]:
        return {
            "ok": False,
            "action": "release_control_checkpoint_import",
            "status": "provisional_release_identity_conflict",
            "checkpoint_path": str(checkpoint_file),
            "mismatches": {
                "source_local_sha256": {
                    "expected": source.get("local_sha256"),
                    "actual": binding["artifact"]["sha256"],
                }
            },
            "state_mutated": False,
        }, 2
    if missing:
        return {
            "ok": False,
            "action": "release_control_checkpoint_import",
            "status": "release_attempt_source_evidence_incomplete",
            "checkpoint_path": str(checkpoint_file),
            "missing_fields": sorted(set(missing)),
            "state_mutated": False,
        }, 2

    source_log = Path(source_log_path) if source_log_path else Path(str(source.get("source_log") or ""))
    if not source_log.is_file():
        return {
            "ok": False,
            "action": "release_control_checkpoint_import",
            "status": "release_attempt_source_log_missing",
            "checkpoint_path": str(checkpoint_file),
            "source_log": str(source_log),
            "state_mutated": False,
        }, 2
    try:
        raw_source = _source_payload(source_log)
    except ReleaseAttemptError as exc:
        return {
            "ok": False,
            "action": "release_control_checkpoint_import",
            "status": "release_attempt_source_log_invalid",
            "checkpoint_path": str(checkpoint_file),
            "source_log": str(source_log),
            "error": str(exc),
            "state_mutated": False,
        }, 2
    comparisons = {
        "requested_filename": raw_source.get("requested_filename") or raw_source.get("source_match_requested"),
        "assigned_filename": raw_source.get("assigned_filename") or raw_source.get("backend_assigned_name"),
        "processed_file_id": raw_source.get("processed_file_id"),
        "library_metadata_object_id": raw_source.get("library_metadata_object_id"),
        "local_sha256": raw_source.get("local_sha256"),
    }
    evidence_mismatches = {
        key: {"expected": source.get(key), "actual": value}
        for key, value in comparisons.items()
        if str(source.get(key) or "") != str(value or "")
    }
    if evidence_mismatches:
        return {
            "ok": False,
            "action": "release_control_checkpoint_import",
            "status": "release_attempt_source_evidence_mismatch",
            "checkpoint_path": str(checkpoint_file),
            "mismatches": evidence_mismatches,
            "state_mutated": False,
        }, 2

    return {
        "ok": True,
        "action": "release_control_checkpoint_import",
        "status": "release_attempt_resumed_project_source_reused",
        "resume": True,
        "reuse_project_source": True,
        "checkpoint_path": str(checkpoint_file),
        "artifact": binding["artifact"],
        "git_commit": git_commit,
        "contract_sha256": contract_sha256,
        "source": source,
        "source_log": str(source_log),
        "state_mutated": False,
    }, 10


def record_project_source(
    checkpoint_path: str | Path,
    *,
    source_log_path: str | Path,
) -> dict[str, Any]:
    checkpoint_file = Path(checkpoint_path)
    source_log = Path(source_log_path)
    checkpoint = _read_json(checkpoint_file)
    _validate_checkpoint_shape(checkpoint)
    payload = _source_payload(source_log)
    artifact = checkpoint.get("artifact") if isinstance(checkpoint.get("artifact"), dict) else {}
    expected_filename = str(artifact.get("filename") or "")
    expected_sha = str(artifact.get("sha256") or "").lower()
    requested = Path(str(payload.get("requested_filename") or payload.get("source_match_requested") or "")).name
    assigned = Path(str(payload.get("assigned_filename") or payload.get("backend_assigned_name") or "")).name
    local_sha = str(payload.get("local_sha256") or "").lower()
    project_url_raw = str(payload.get("project_url") or "")
    project_id, project_url = _project_identity(project_url_raw)
    source = {
        "requested_filename": requested,
        "assigned_filename": assigned,
        "processed_file_id": str(payload.get("processed_file_id") or ""),
        "library_metadata_object_id": str(payload.get("library_metadata_object_id") or ""),
        "project_id": project_id,
        "project_url": project_url,
        "local_sha256": local_sha,
        "local_size_bytes": payload.get("local_size_bytes"),
        "persistence_verified": payload.get("persistence_verified") is True,
        "replacement_backing_identity_verified": payload.get("replacement_backing_identity_verified") is True,
        "family_replacement_verified": payload.get("family_replacement_verified") is True,
        "final_family_source_count": payload.get("final_family_source_count"),
        "source_log": str(source_log),
    }
    checks = {
        "requested_filename_exact": requested == expected_filename,
        "assigned_filename_present": bool(assigned),
        "processed_file_id_present": source["processed_file_id"].startswith("file_"),
        "library_metadata_object_id_present": source["library_metadata_object_id"].startswith("libfile_"),
        "project_identity_present": bool(project_id and project_url),
        "artifact_sha256_exact": bool(expected_sha) and local_sha == expected_sha,
        "persistence_verified": source["persistence_verified"],
        "replacement_backing_identity_verified": source["replacement_backing_identity_verified"],
        "family_replacement_verified": source["family_replacement_verified"],
        "final_family_singleton": int(source["final_family_source_count"] or 0) == 1,
    }
    if not all(checks.values()):
        raise ReleaseAttemptError("Project Source evidence failed provisional identity checks: " + json.dumps(checks, sort_keys=True))
    now = _utc_now()
    checkpoint["source"] = source
    checkpoint["status"] = "published_pending_validation"
    checkpoint["updated_at"] = now
    phases = checkpoint.setdefault("phase_results", [])
    phases.append(
        {
            "phase": "project-source-publish",
            "ok": True,
            "status": "project_source_published_and_bound",
            "artifact_sha256": expected_sha,
            "assigned_filename": assigned,
            "processed_file_id": source["processed_file_id"],
            "library_metadata_object_id": source["library_metadata_object_id"],
            "recorded_at": now,
        }
    )
    _atomic_write_json(checkpoint_file, checkpoint)
    return {
        "ok": True,
        "action": "release_control_checkpoint_record_source",
        "status": "provisional_release_identity_bound",
        "checkpoint_path": str(checkpoint_file),
        "artifact": artifact,
        "source": source,
        "checks": checks,
    }


def record_adoption(
    checkpoint_path: str | Path,
    *,
    adoption_log_path: str | Path,
    current_log_path: str | Path,
) -> dict[str, Any]:
    checkpoint_file = Path(checkpoint_path)
    checkpoint = _read_json(checkpoint_file)
    _validate_checkpoint_shape(checkpoint)
    adoption_log = Path(adoption_log_path)
    current_log = Path(current_log_path)
    adoption_objects = _extract_json_objects(adoption_log)
    current_objects = _extract_json_objects(current_log)
    adoption = next((value for value in reversed(adoption_objects) if value.get("ok") is True), None)
    current = next((value for value in reversed(current_objects) if value.get("ok") is True), None)
    if adoption is None or current is None:
        raise ReleaseAttemptError("adoption/current evidence is incomplete")
    now = _utc_now()
    checkpoint["adoption"] = {
        "status": adoption.get("status"),
        "assigned_source_ref": adoption.get("assigned_source_ref"),
        "processed_file_id": adoption.get("processed_file_id"),
        "library_metadata_object_id": adoption.get("library_metadata_object_id"),
        "adoption_log": str(adoption_log),
        "current_log": str(current_log),
    }
    checkpoint["status"] = "release_adopted_and_verified"
    checkpoint["updated_at"] = now
    checkpoint.setdefault("phase_results", []).append(
        {
            "phase": "adoption",
            "ok": True,
            "status": "release_adopted_and_verified",
            "recorded_at": now,
        }
    )
    _atomic_write_json(checkpoint_file, checkpoint)
    return {
        "ok": True,
        "action": "release_control_checkpoint_record_adoption",
        "status": "release_adopted_and_verified",
        "checkpoint_path": str(checkpoint_file),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Promptbranch release-control attempt checkpoint helper")
    sub = parser.add_subparsers(dest="command", required=True)

    preflight = sub.add_parser("preflight")
    preflight.add_argument("--checkpoint", required=True)
    preflight.add_argument("--repo-id", required=True)
    preflight.add_argument("--version", required=True)
    preflight.add_argument("--artifact", required=True)
    preflight.add_argument("--git-commit", required=True)
    preflight.add_argument("--contract-sha256", required=True)
    preflight.add_argument("--source-log")

    source = sub.add_parser("record-source")
    source.add_argument("--checkpoint", required=True)
    source.add_argument("--source-log", required=True)

    adoption = sub.add_parser("record-adoption")
    adoption.add_argument("--checkpoint", required=True)
    adoption.add_argument("--adoption-log", required=True)
    adoption.add_argument("--current-log", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    ns = _build_parser().parse_args(argv)
    try:
        if ns.command == "preflight":
            payload, rc = preflight_checkpoint(
                ns.checkpoint,
                repo_id=ns.repo_id,
                version=ns.version,
                artifact_path=ns.artifact,
                git_commit=ns.git_commit,
                contract_sha256=ns.contract_sha256,
                source_log_path=ns.source_log,
            )
        elif ns.command == "record-source":
            payload = record_project_source(ns.checkpoint, source_log_path=ns.source_log)
            rc = 0
        else:
            payload = record_adoption(
                ns.checkpoint,
                adoption_log_path=ns.adoption_log,
                current_log_path=ns.current_log,
            )
            rc = 0
    except (ReleaseAttemptError, OSError, ValueError) as exc:
        payload = {
            "ok": False,
            "action": f"release_control_checkpoint_{ns.command.replace('-', '_')}",
            "status": "release_control_checkpoint_failed",
            "error": str(exc),
        }
        rc = 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
