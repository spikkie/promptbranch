from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

IDENTITY_SCHEMA = "promptbranch.release.identity"
IDENTITY_SCHEMA_VERSION = "1.0"


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evaluate_current_release_identity(
    current_payload: dict[str, Any] | None,
    *,
    repo_id: str,
    version: str,
    artifact_filename: str,
    artifact_sha256: str,
) -> dict[str, Any]:
    """Classify a candidate against accepted/current state without mutation.

    A previously adopted version is immutable. The same version and hash is an
    idempotent identity; the same version with a different or missing hash is a
    release-blocking conflict.
    """

    payload = current_payload if isinstance(current_payload, dict) else {}
    base = {
        "schema": IDENTITY_SCHEMA,
        "schema_version": IDENTITY_SCHEMA_VERSION,
        "repo_id": repo_id,
        "candidate_version": version,
        "candidate_artifact": artifact_filename,
        "candidate_sha256": artifact_sha256,
    }
    if payload.get("ok") is not True:
        return {
            **base,
            "ok": False,
            "status": "release_identity_current_unavailable",
            "already_current": False,
            "conflict": True,
            "current_payload": current_payload,
        }
    repos = payload.get("repos") if isinstance(payload.get("repos"), dict) else {}
    selected = repos.get(repo_id) if isinstance(repos.get(repo_id), dict) else None
    base = {**base, "selected_repo": selected}
    if selected is None:
        return {**base, "ok": True, "status": "new_release_identity", "already_current": False, "conflict": False}

    state = selected.get("state") if isinstance(selected.get("state"), dict) else {}
    current = selected.get("registry_current") if isinstance(selected.get("registry_current"), dict) else {}
    consistency = selected.get("consistency") if isinstance(selected.get("consistency"), dict) else {}
    current_version = str(current.get("version") or state.get("artifact_version") or "")
    current_sha = str(current.get("sha256") or "")
    current_artifact = str(current.get("filename") or state.get("artifact_ref") or "")
    details = {
        "current_version": current_version or None,
        "current_artifact": current_artifact or None,
        "current_sha256": current_sha or None,
        "state": state,
        "registry_current": current,
        "consistency": consistency,
    }
    if current_version != version:
        return {**base, **details, "ok": True, "status": "new_release_identity", "already_current": False, "conflict": False}
    if not current_sha:
        return {**base, **details, "ok": False, "status": "immutable_release_identity_hash_missing", "already_current": False, "conflict": True}
    if current_sha != artifact_sha256:
        return {**base, **details, "ok": False, "status": "immutable_release_identity_conflict", "already_current": False, "conflict": True}

    exact = bool(
        current_artifact == artifact_filename
        and state.get("artifact_ref") == artifact_filename
        and state.get("artifact_version") == version
        and current.get("filename") == artifact_filename
        and current.get("version") == version
        and consistency.get("registry_current_matches_state_artifact") is True
        and consistency.get("state_source_matches_state_artifact") is True
    )
    if not exact:
        return {**base, **details, "ok": False, "status": "immutable_release_identity_state_mismatch", "already_current": False, "conflict": True}
    return {**base, **details, "ok": True, "status": "release_identity_already_current", "already_current": True, "conflict": False}
