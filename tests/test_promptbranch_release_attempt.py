from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
import zipfile
from pathlib import Path

from promptbranch_release_attempt import preflight_checkpoint, record_project_source

ROOT = Path(__file__).resolve().parents[1]


def _artifact(path: Path, payload: bytes = b"release-bytes") -> Path:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("VERSION", "v1.2.3\n")
        archive.writestr("payload.bin", payload)
    return path


def _source_log(path: Path, artifact: Path, *, assigned: str = "demo_v1.2.3(1).zip") -> Path:
    payload = {
        "ok": True,
        "action": "add",
        "status": "source_added",
        "project_url": "https://chatgpt.com/g/g-p-demo/project",
        "requested_filename": artifact.name,
        "assigned_filename": assigned,
        "processed_file_id": "file_00000000000000000000000000000001",
        "library_metadata_object_id": "libfile_00000000000000000000000000000001",
        "persistence_verified": True,
        "replacement_backing_identity_verified": True,
        "family_replacement_verified": True,
        "final_family_source_count": 1,
        "local_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "local_size_bytes": artifact.stat().st_size,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def test_failed_validation_cleanup_rerun_preserves_provisional_identity(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "demo_v1.2.3.zip")
    checkpoint = tmp_path / "release-control-checkpoint.json"
    source_log = _source_log(tmp_path / "source-add.json", artifact)
    binding = {
        "repo_id": "demo",
        "version": "v1.2.3",
        "artifact_path": artifact,
        "git_commit": "a" * 40,
        "contract_sha256": "b" * 64,
        "source_log_path": source_log,
    }

    first, first_rc = preflight_checkpoint(checkpoint, **binding)
    assert first_rc == 0
    assert first["status"] == "new_release_attempt_bound"
    published = record_project_source(checkpoint, source_log_path=source_log)
    assert published["status"] == "provisional_release_identity_bound"

    # Simulate validation failure and cleanup. The release artifact, Git commit,
    # release contract and authoritative source evidence remain unchanged.
    transient = tmp_path / "validation-work"
    transient.mkdir()
    (transient / "partial.log").write_text("failed\n", encoding="utf-8")
    for child in transient.iterdir():
        child.unlink()
    transient.rmdir()

    resumed, resumed_rc = preflight_checkpoint(checkpoint, **binding)
    assert resumed_rc == 10
    assert resumed["status"] == "release_attempt_resumed_project_source_reused"
    assert resumed["artifact"]["sha256"] == first["artifact"]["sha256"]
    assert resumed["git_commit"] == "a" * 40
    assert resumed["source"]["assigned_filename"] == "demo_v1.2.3(1).zip"
    assert resumed["source"]["processed_file_id"] == "file_00000000000000000000000000000001"
    assert resumed["source"]["library_metadata_object_id"] == "libfile_00000000000000000000000000000001"
    assert resumed["state_mutated"] is False


def test_same_version_changed_bytes_fail_before_source_mutation(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "demo_v1.2.3.zip")
    checkpoint = tmp_path / "release-control-checkpoint.json"
    source_log = _source_log(tmp_path / "source-add.json", artifact)
    args = {
        "repo_id": "demo",
        "version": "v1.2.3",
        "artifact_path": artifact,
        "git_commit": "a" * 40,
        "contract_sha256": "b" * 64,
        "source_log_path": source_log,
    }
    _, rc = preflight_checkpoint(checkpoint, **args)
    assert rc == 0
    record_project_source(checkpoint, source_log_path=source_log)

    _artifact(artifact, b"different-release-bytes")
    blocked, blocked_rc = preflight_checkpoint(checkpoint, **args)
    assert blocked_rc == 2
    assert blocked["status"] == "provisional_release_identity_conflict"
    assert blocked["state_mutated"] is False


def test_deterministic_builder_is_byte_identical_across_mtime_changes(tmp_path: Path) -> None:
    repo = tmp_path / "demo-repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.3\n", encoding="utf-8")
    (repo / ".not_to_zip").write_text("*.zip\n__pycache__/\n", encoding="utf-8")
    (repo / "alpha.txt").write_text("alpha\n", encoding="utf-8")
    script = repo / "run.sh"
    script.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
    script.chmod(0o755)
    nested = repo / "nested"
    nested.mkdir()
    (nested / "beta.txt").write_text("beta\n", encoding="utf-8")

    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    builder = ROOT / "scripts" / "build-release-artifact.py"
    subprocess.run(["python3", str(builder), "--repo", str(repo), "--output", str(first)], check=True)

    future = time.time() + 10000
    for path in repo.rglob("*"):
        os.utime(path, (future, future), follow_symlinks=False)
    subprocess.run(["python3", str(builder), "--repo", str(repo), "--output", str(second)], check=True)

    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(first) as archive:
        assert all(info.date_time == (2020, 1, 1, 0, 0, 0) for info in archive.infolist())
        assert all(info.compress_type == zipfile.ZIP_STORED for info in archive.infolist())
        assert archive.getinfo("run.sh").external_attr >> 16 & 0o777 == 0o755


def test_release_control_imports_checkpoint_before_project_source_mutation() -> None:
    script = (ROOT / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    assert 'default_packager="${repo_root}/scripts/build-release-artifact.py"' in script
    assert "Deterministic canonical rebuild verified" in script
    assert "provisional_release_identity_conflict" in (ROOT / "promptbranch_release_attempt.py").read_text(encoding="utf-8")
    checkpoint_index = script.index("release_control_checkpoint_preflight", script.index("# Add release ZIP"))
    source_add_index = script.index('promptbranch src add "${canonical_artifact_zip}"', checkpoint_index)
    assert checkpoint_index < source_add_index
    assert "release_attempt_resumed_project_source_reused" in (ROOT / "promptbranch_release_attempt.py").read_text(encoding="utf-8")
    assert "Project Source add skipped: imported checkpoint preserves exact provisional version/hash/source identity" in script
