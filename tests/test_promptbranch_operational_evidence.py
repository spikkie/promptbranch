from __future__ import annotations

import json
from pathlib import Path

from promptbranch_operational_evidence import (
    REQUIRED_TOP_LEVEL_STEPS,
    build_operational_lifecycle_evidence,
    validate_operational_lifecycle_evidence,
)


def _write(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return path


def _fixture(tmp_path: Path) -> tuple[Path, dict[str, Path]]:
    import hashlib

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v0.1.115.1\n", encoding="utf-8")
    artifact = repo / "chatgpt_claudecode_workflow-2_v0.1.115.1.zip"
    artifact.write_bytes(b"candidate")
    artifact_sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
    assigned = artifact.name.replace(".zip", "(1).zip")
    repo_id = "chatgpt_claudecode_workflow-2"
    steps = [{"name": name, "ok": True, "skipped": False} for name in sorted(REQUIRED_TOP_LEVEL_STEPS)]
    files = {
        "summary": _write(tmp_path / "summary.json", {
            "ok": True, "final_verdict": "GO", "step_count": 10,
            "failure_count": 0, "skipped_count": 0, "steps": steps,
        }),
        "guard": _write(tmp_path / "guard.json", {"ok": True, "status": "guard_passed", "failure_count": 0}),
        "adopt": _write(tmp_path / "adopt.json", {
            "ok": True, "status": "adopted", "repo_id": repo_id,
            "requested_source_ref": artifact.name, "assigned_source_ref": assigned,
            "processed_file_id": "file_123", "library_metadata_object_id": "libfile_123",
            "source_verified": True, "source_evidence_verified": True,
            "artifact_registry_updated": True, "state_artifact_updated": True,
            "state_source_updated": True,
            "source_verification": {"project_source_mutated": False},
        }),
        "current": _write(tmp_path / "current.json", {
            "ok": True, "action": "artifact_current_all", "status": "artifact_registry_loaded",
            "repos": {repo_id: {
                "ok": True, "status": "artifact_registry_loaded", "repo_id": repo_id,
                "runtime": {"version": "v0.1.115.1"},
                "state": {"artifact_version": "v0.1.115.1", "source_ref": assigned},
                "registry_current": {"version": "v0.1.115.1", "filename": artifact.name, "sha256": artifact_sha},
                "consistency": {
                    "registry_current_matches_state_artifact": True,
                    "state_source_matches_state_artifact": True,
                    "code_version_matches_state_source": True,
                },
            }},
        }),
        "source": _write(tmp_path / "source.json", {
            "ok": True, "status": "source_evidence_verified",
            "requested_filename": artifact.name, "assigned_filename": assigned,
            "processed_file_id": "file_123", "library_metadata_object_id": "libfile_123",
            "repo_id": repo_id,
            "checks": {"requested_filename_exact": True, "assigned_filename_present": True},
        }),
        "artifact": artifact,
    }
    return repo, files


def test_build_and_validate_operational_lifecycle_evidence(tmp_path: Path) -> None:
    repo, files = _fixture(tmp_path)
    evidence = build_operational_lifecycle_evidence(
        repo_path=repo,
        all_tests_summary=files["summary"], artifact_guard=files["guard"],
        adoption_result=files["adopt"], current_result=files["current"],
        source_evidence=files["source"], artifact=files["artifact"],
    )
    assert evidence["ok"] is True, evidence["errors"]
    assert evidence["proven_level"] == "operational"
    assert all(evidence["operational_dimensions"].values())
    result = validate_operational_lifecycle_evidence(evidence, repo_path=repo)
    assert result["ok"] is True
    assert result["status"] == "operational_validated"


def test_operational_evidence_rejects_missing_release_step(tmp_path: Path) -> None:
    repo, files = _fixture(tmp_path)
    summary = json.loads(files["summary"].read_text())
    summary["steps"] = summary["steps"][:-1]
    summary["step_count"] = 9
    _write(files["summary"], summary)
    evidence = build_operational_lifecycle_evidence(
        repo_path=repo,
        all_tests_summary=files["summary"], artifact_guard=files["guard"],
        adoption_result=files["adopt"], current_result=files["current"],
        source_evidence=files["source"], artifact=files["artifact"],
    )
    assert evidence["ok"] is False
    assert evidence["proven_level"] == "executable"


def test_operational_evidence_hash_is_tamper_evident(tmp_path: Path) -> None:
    repo, files = _fixture(tmp_path)
    evidence = build_operational_lifecycle_evidence(
        repo_path=repo,
        all_tests_summary=files["summary"], artifact_guard=files["guard"],
        adoption_result=files["adopt"], current_result=files["current"],
        source_evidence=files["source"], artifact=files["artifact"],
    )
    evidence["artifact"]["sha256"] = "0" * 64
    result = validate_operational_lifecycle_evidence(evidence, repo_path=repo)
    assert result["ok"] is False
    assert any("hash mismatch" in error for error in result["errors"])
