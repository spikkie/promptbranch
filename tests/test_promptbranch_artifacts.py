from __future__ import annotations

import json
import zipfile
from pathlib import Path

from promptbranch_artifacts import ArtifactRegistry, create_repo_snapshot, default_artifact_filename, iter_repo_files, verify_zip_artifact


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
    (repo / ".promptbranch-service-start.0.0.189.pid").write_text("12345\n", encoding="utf-8")
    (repo / ".pytest_cache" / "v" / "cache").mkdir(parents=True)
    (repo / ".pytest_cache" / "v" / "cache" / "nodeids").write_text("[]", encoding="utf-8")
    (repo / "__pycache__").mkdir()
    (repo / "__pycache__" / "app.cpython-312.pyc").write_bytes(b"pyc")
    (repo / "pkg").mkdir()
    (repo / "pkg" / "module.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "pkg" / "__pycache__").mkdir()
    (repo / "pkg" / "__pycache__" / "module.cpython-312.pyc").write_bytes(b"pyc")

    registry = ArtifactRegistry(tmp_path / "profile")
    record, included = create_repo_snapshot(repo, output_dir=registry.artifact_dir)

    assert record.filename == "repo_v0.1.0.zip"
    assert "VERSION" in included
    assert "app.py" in included
    assert "pkg/module.py" in included
    assert ".env" not in included
    assert "old.zip" not in included
    assert ".pb_profile/state.json" not in included
    assert ".promptbranch-service-start.0.0.189.pid" not in included
    assert not any(".pytest_cache" in item for item in included)
    assert not any("__pycache__" in item for item in included)
    assert not any(item.endswith(".pyc") for item in included)

    with zipfile.ZipFile(record.path) as archive:
        names = archive.namelist()
        assert sorted(names) == sorted(included)
        assert not any(".pytest_cache" in name or "__pycache__" in name or name.endswith(".pyc") for name in names)


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


def test_iter_repo_files_excludes_log_derivatives(tmp_path) -> None:
    (tmp_path / "VERSION").write_text("v1.0.0\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "pb_test.full.v1.log").write_text("log", encoding="utf-8")
    (tmp_path / "pb_test.full.v1.log.report").write_text("report", encoding="utf-8")
    (tmp_path / "pb_test.full.v1.import-smoke.json.log").write_text("jsonlog", encoding="utf-8")

    names = [path.relative_to(tmp_path).as_posix() for path in iter_repo_files(tmp_path)]

    assert "main.py" in names
    assert "pb_test.full.v1.log" not in names
    assert "pb_test.full.v1.log.report" not in names
    assert "pb_test.full.v1.import-smoke.json.log" not in names
