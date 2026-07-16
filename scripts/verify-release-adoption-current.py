#!/usr/bin/env python3
"""Verify the final artifact-current state after release adoption."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterator


CONSISTENCY_KEYS = (
    "registry_current_matches_state_artifact",
    "state_source_matches_state_artifact",
    "code_version_matches_state_source",
)


def _load_json_object(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    index = raw.find("{")
    if index < 0:
        raise ValueError(f"no JSON object found in {path}")
    value = json.loads(raw[index:])
    if not isinstance(value, dict):
        raise ValueError(f"JSON root in {path} is not an object")
    return value


def _artifact_current_entries(payload: dict[str, Any]) -> Iterator[tuple[str | None, dict[str, Any]]]:
    repos = payload.get("repos")
    if isinstance(repos, dict):
        for repo_id in sorted(repos):
            repo_payload = repos.get(repo_id)
            if isinstance(repo_payload, dict):
                yield str(repo_id), repo_payload
        return
    if any(isinstance(payload.get(key), dict) for key in ("runtime", "state", "registry_current", "baseline_roles")):
        scope = payload.get("scope") if isinstance(payload.get("scope"), dict) else {}
        repo_id = scope.get("repo_id")
        yield str(repo_id) if repo_id else None, payload


def _name(value: object) -> str:
    return Path(str(value or "")).name


def _expected_source_identity(
    canonical_artifact_name: str,
    evidence_path: Path | None,
) -> tuple[dict[str, str | None], dict[str, Any] | None]:
    if evidence_path is None:
        return {
            "assigned_source_filename": canonical_artifact_name,
            "processed_file_id": None,
            "library_metadata_object_id": None,
            "repo_id": None,
        }, None

    evidence = _load_json_object(evidence_path)
    expected = {
        "assigned_source_filename": _name(evidence.get("assigned_filename")),
        "processed_file_id": str(evidence.get("processed_file_id") or "").strip(),
        "library_metadata_object_id": str(evidence.get("library_metadata_object_id") or "").strip(),
        "repo_id": str(evidence.get("repo_id") or "").strip() or None,
    }
    required = {
        "evidence_ok": evidence.get("ok") is True,
        "evidence_status": evidence.get("status") == "source_evidence_verified",
        "assigned_source_filename_present": bool(expected["assigned_source_filename"]),
        "processed_file_id_present": str(expected["processed_file_id"] or "").startswith("file_"),
        "library_metadata_object_id_present": str(expected["library_metadata_object_id"] or "").startswith("libfile_"),
    }
    if not all(required.values()):
        raise ValueError(f"source adoption evidence is incomplete: {json.dumps(required, sort_keys=True)}")
    return expected, evidence


def verify(
    current_path: Path,
    expected_version: str,
    expected_artifact: Path,
    evidence_path: Path | None,
) -> dict[str, Any]:
    payload = _load_json_object(current_path)
    if payload.get("ok") is not True:
        raise ValueError("artifact current did not return ok:true")

    canonical_name = expected_artifact.name
    expected_source, _evidence = _expected_source_identity(canonical_name, evidence_path)
    checked: list[dict[str, Any]] = []

    for repo_id, repo_payload in _artifact_current_entries(payload):
        runtime = repo_payload.get("runtime") if isinstance(repo_payload.get("runtime"), dict) else {}
        state = repo_payload.get("state") if isinstance(repo_payload.get("state"), dict) else {}
        registry = repo_payload.get("registry_current") if isinstance(repo_payload.get("registry_current"), dict) else {}
        consistency = repo_payload.get("consistency") if isinstance(repo_payload.get("consistency"), dict) else {}

        values = {
            "runtime.version": runtime.get("version"),
            "state.artifact_version": state.get("artifact_version"),
            "state.source_version": state.get("source_version"),
            "registry_current.version": registry.get("version"),
        }
        refs = {
            "state.artifact_ref": _name(state.get("artifact_ref")),
            "state.source_ref": _name(state.get("source_ref")),
            "registry_current.filename": _name(registry.get("filename")),
        }
        backing_identity = {
            "registry_current.source_processed_file_id": registry.get("source_processed_file_id"),
            "registry_current.source_library_metadata_object_id": registry.get("source_library_metadata_object_id"),
        }
        checks = {
            "runtime_version_matches": values["runtime.version"] == expected_version,
            "state_artifact_version_matches": values["state.artifact_version"] == expected_version,
            "state_source_version_matches": values["state.source_version"] == expected_version,
            "registry_current_version_matches": values["registry_current.version"] == expected_version,
            "state_artifact_ref_matches_canonical": refs["state.artifact_ref"] == canonical_name,
            "registry_current_filename_matches_canonical": refs["registry_current.filename"] == canonical_name,
            "state_source_ref_matches_assigned": refs["state.source_ref"] == expected_source["assigned_source_filename"],
            "registry_current_matches_state_artifact": consistency.get("registry_current_matches_state_artifact") is True,
            "state_source_matches_state_artifact": consistency.get("state_source_matches_state_artifact") is True,
            "code_version_matches_state_source": consistency.get("code_version_matches_state_source") is True,
        }
        if evidence_path is not None:
            checks.update(
                {
                    "registry_processed_file_id_matches_evidence": (
                        backing_identity["registry_current.source_processed_file_id"] == expected_source["processed_file_id"]
                    ),
                    "registry_library_metadata_object_id_matches_evidence": (
                        backing_identity["registry_current.source_library_metadata_object_id"]
                        == expected_source["library_metadata_object_id"]
                    ),
                    "repo_id_matches_evidence": expected_source["repo_id"] in (None, repo_id),
                }
            )

        diagnostic = {
            "repo_id": repo_id,
            "values": values,
            "refs": refs,
            "backing_identity": backing_identity,
            "consistency": {key: consistency.get(key) for key in CONSISTENCY_KEYS},
            "checks": checks,
        }
        checked.append(diagnostic)
        if all(checks.values()):
            return {
                "schema": "promptbranch.release_control.adoption_verification",
                "schema_version": "1.0",
                "ok": True,
                "status": "release_adopted_and_verified",
                "expected_version": expected_version,
                "canonical_artifact_filename": canonical_name,
                "assigned_source_filename": expected_source["assigned_source_filename"],
                "processed_file_id": expected_source["processed_file_id"],
                "library_metadata_object_id": expected_source["library_metadata_object_id"],
                "matched_repo_id": repo_id,
                "verification_mode": "assigned_source_evidence" if evidence_path is not None else "canonical_source_ref",
                "checks": checks,
                "current_json": str(current_path),
                "source_evidence_json": str(evidence_path) if evidence_path is not None else None,
            }

    return {
        "schema": "promptbranch.release_control.adoption_verification",
        "schema_version": "1.0",
        "ok": False,
        "status": "release_adoption_verification_failed",
        "expected_version": expected_version,
        "canonical_artifact_filename": canonical_name,
        "assigned_source_filename": expected_source["assigned_source_filename"],
        "processed_file_id": expected_source["processed_file_id"],
        "library_metadata_object_id": expected_source["library_metadata_object_id"],
        "checked": checked,
        "current_json": str(current_path),
        "source_evidence_json": str(evidence_path) if evidence_path is not None else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("current_json", type=Path)
    parser.add_argument("expected_version")
    parser.add_argument("expected_artifact", type=Path)
    parser.add_argument("--source-evidence-json", type=Path)
    args = parser.parse_args()

    try:
        result = verify(args.current_json, args.expected_version, args.expected_artifact, args.source_evidence_json)
    except Exception as exc:
        result = {
            "schema": "promptbranch.release_control.adoption_verification",
            "schema_version": "1.0",
            "ok": False,
            "status": "release_adoption_verification_failed",
            "error": str(exc),
            "current_json": str(args.current_json),
            "source_evidence_json": str(args.source_evidence_json) if args.source_evidence_json else None,
        }

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
