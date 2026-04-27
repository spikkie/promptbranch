from __future__ import annotations

import json
import zipfile
from pathlib import Path

from promptbranch_artifacts import ArtifactRegistry, create_repo_snapshot, default_artifact_filename, verify_zip_artifact


def test_default_artifact_filename_prefers_version_file(tmp_path: Path) -> None:
    repo = tmp_path / "demo_repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.3\n", encoding="utf-8")

    filename, version = default_artifact_filename(repo)

    assert filename == "demo_repo_v1.2.3.zip"
    assert version == "v1.2.3"


def test_create_repo_snapshot_excludes_generated_and_profile_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v0.1.0\n", encoding="utf-8")
    (repo / "app.py").write_text("print('ok')\n", encoding="utf-8")
    (repo / ".env").write_text("SECRET=1\n", encoding="utf-8")
    (repo / "old.zip").write_bytes(b"zip")
    (repo / ".pb_profile").mkdir()
    (repo / ".pb_profile" / "state.json").write_text("{}", encoding="utf-8")

    registry = ArtifactRegistry(tmp_path / "profile")
    record, included = create_repo_snapshot(repo, output_dir=registry.artifact_dir)

    assert record.filename == "repo_v0.1.0.zip"
    assert "VERSION" in included
    assert "app.py" in included
    assert ".env" not in included
    assert "old.zip" not in included
    assert ".pb_profile/state.json" not in included

    with zipfile.ZipFile(record.path) as archive:
        assert sorted(archive.namelist()) == sorted(included)


def test_artifact_registry_round_trip_and_verify(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v0.1.0\n", encoding="utf-8")
    (repo / "README.md").write_text("# demo\n", encoding="utf-8")

    registry = ArtifactRegistry(tmp_path / "profile")
    record, _ = create_repo_snapshot(repo, output_dir=registry.artifact_dir)
    stored = registry.add(record)

    assert registry.current()["filename"] == stored["filename"]
    assert json.loads(registry.path.read_text(encoding="utf-8"))["artifacts"][0]["filename"] == "repo_v0.1.0.zip"

    verify = verify_zip_artifact(record.path)
    assert verify["ok"] is True
    assert verify["wrapper_folder"] is None
    assert verify["has_version_file"] is True
