from __future__ import annotations

import json
import zipfile
from pathlib import Path

from promptbranch_artifacts import ArtifactRegistry, create_repo_snapshot, default_artifact_filename, iter_repo_files, release_entry_hygiene_violations, verify_zip_artifact


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
    (repo / ".promptbranch-service-start.0.0.190.pid").write_text("12345\n", encoding="utf-8")
    (repo / "task_69fd0a71-3cb8-8397-bd09-9be7fcccafe1_message.txt").write_text("transcript", encoding="utf-8")
    (repo / "task_show_69f85be3-db68-838a-b6c8-66a2c7c40be9_messages.txt").write_text("transcript", encoding="utf-8")
    (repo / "session_20260508_004724.log").write_text("session", encoding="utf-8")
    (repo / "stdout.json").write_text("{}", encoding="utf-8")
    (repo / "stderr.txt").write_text("err", encoding="utf-8")
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
    assert ".promptbranch-service-start.0.0.190.pid" not in included
    assert "task_69fd0a71-3cb8-8397-bd09-9be7fcccafe1_message.txt" not in included
    assert "task_show_69f85be3-db68-838a-b6c8-66a2c7c40be9_messages.txt" not in included
    assert "session_20260508_004724.log" not in included
    assert "stdout.json" not in included
    assert "stderr.txt" not in included
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


def test_release_entry_hygiene_violations_flags_transcripts_logs_and_nested_archives() -> None:
    names = [
        "VERSION",
        "src/app.py",
        "task_69fd0a71-3cb8-8397-bd09-9be7fcccafe1_message.txt",
        "task_show_69f85be3-db68-838a-b6c8-66a2c7c40be9_messages.txt",
        "session_20260508_004724.log",
        "nested/release.zip",
        "pkg/__pycache__/module.cpython-312.pyc",
        "stdout.json",
        "stderr.txt",
    ]

    bad = release_entry_hygiene_violations(names)

    assert "VERSION" not in bad
    assert "src/app.py" not in bad
    assert "task_69fd0a71-3cb8-8397-bd09-9be7fcccafe1_message.txt" in bad
    assert "task_show_69f85be3-db68-838a-b6c8-66a2c7c40be9_messages.txt" in bad
    assert "session_20260508_004724.log" in bad
    assert "nested/release.zip" in bad
    assert "pkg/__pycache__/module.cpython-312.pyc" in bad
    assert "stdout.json" in bad
    assert "stderr.txt" in bad


def test_verify_zip_artifact_rejects_generated_task_transcript(tmp_path: Path) -> None:
    zip_path = tmp_path / "bad.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("VERSION", "v0.1.0\n")
        archive.writestr("task_69fd0a71-3cb8-8397-bd09-9be7fcccafe1_message.txt", "transcript")

    payload = verify_zip_artifact(zip_path)

    assert payload["ok"] is False
    assert payload["hygiene_violation_count"] == 1
    assert payload["hygiene_violations"] == ["task_69fd0a71-3cb8-8397-bd09-9be7fcccafe1_message.txt"]
