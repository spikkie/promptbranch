from __future__ import annotations

import json
import zipfile
from pathlib import Path

from promptbranch_artifacts import ArtifactIdentityConflictError, ArtifactRecord, ArtifactRegistry, canonical_artifact_filename, canonical_version_tag, create_repo_snapshot, default_artifact_filename, infer_repo_id_from_artifact_filename, iter_repo_files, parse_canonical_artifact_filename, release_entry_hygiene_violations, verify_zip_artifact


def test_canonical_artifact_filename_accepts_extended_numeric_versions() -> None:
    assert canonical_artifact_filename("architecture-process", "0.29.0") == "architecture-process_v0.29.0.zip"
    assert canonical_artifact_filename("ib_forex_trading", "v0.248.3.1") == "ib_forex_trading_v0.248.3.1.zip"
    assert canonical_artifact_filename("candlecast-src", "0.19.5.94.1") == "candlecast-src_v0.19.5.94.1.zip"
    assert canonical_version_tag("vv0.19.5.94.1") == "v0.19.5.94.1"


def test_parse_canonical_artifact_filename_rejects_legacy_names() -> None:
    assert parse_canonical_artifact_filename("architecture-process_v0.29.0.zip") == {"repo_id": "architecture-process", "version": "v0.29.0"}
    assert parse_canonical_artifact_filename("architecture-process_0.29.0.zip") is None
    assert parse_canonical_artifact_filename("ib_forex_trading.0.248.3.1.zip") is None
    assert infer_repo_id_from_artifact_filename("architecture-process_0.29.0.zip") is None


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
    (repo / "6a062d16-35f4-8387-9217-1d2bd9dde63f.task.show").write_text("task transcript\n", encoding="utf-8")
    (repo / ".pb_profile").mkdir()
    (repo / ".pb_profile" / "state.json").write_text("{}", encoding="utf-8")
    (repo / ".pb_profile" / "ask_records" / "req-demo").mkdir(parents=True)
    (repo / ".pb_profile" / "ask_records" / "req-demo" / "reply.parsed.json").write_text("{}", encoding="utf-8")
    (repo / ".pb_profile" / "ask_protocol_runs").mkdir(parents=True)
    (repo / ".pb_profile" / "ask_protocol_runs" / "req-demo.json").write_text("{}", encoding="utf-8")
    (repo / ".pb_profile" / "release_logs" / "v0.0.222").mkdir(parents=True)
    (repo / ".pb_profile" / "release_logs" / "v0.0.222" / "pb_ask_protocol_smoke.v0.0.222.json").write_text("{}", encoding="utf-8")
    (repo / ".promptbranch-service-start.0.0.195.pid").write_text("12345\n", encoding="utf-8")
    (repo / "task_69fd0a71-3cb8-8397-bd09-9be7fcccafe1_message.txt").write_text("transcript", encoding="utf-8")
    (repo / "task_show_69f85be3-db68-838a-b6c8-66a2c7c40be9_messages.txt").write_text("transcript", encoding="utf-8")
    (repo / "task_69fd0f07-8a28-8395-8f3d-cb6d758965d7.messages.txt").write_text("transcript", encoding="utf-8")
    (repo / "session_20260508_004724.log").write_text("session", encoding="utf-8")
    (repo / "stdout.json").write_text("{}", encoding="utf-8")
    (repo / "stderr.txt").write_text("err", encoding="utf-8")
    (repo / "pb_artifact_adopt.v0.0.196.json").write_text("{}", encoding="utf-8")
    (repo / "pb_artifact_current.v0.0.196.json").write_text("{}", encoding="utf-8")
    (repo / "pb_artifact_verify.v0.0.196.json").write_text("{}", encoding="utf-8")
    (repo / "pb_src_list.before_adopt.v0.0.196.json").write_text("{}", encoding="utf-8")
    (repo / "pb_test.full.v0.0.196.report.json").write_text("{}", encoding="utf-8")
    (repo / "promptbranch-project-list.json").write_text("{}", encoding="utf-8")
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
    assert "6a062d16-35f4-8387-9217-1d2bd9dde63f.task.show" not in included
    assert ".pb_profile/state.json" not in included
    assert ".promptbranch-service-start.0.0.195.pid" not in included
    assert "task_69fd0a71-3cb8-8397-bd09-9be7fcccafe1_message.txt" not in included
    assert "task_show_69f85be3-db68-838a-b6c8-66a2c7c40be9_messages.txt" not in included
    assert "task_69fd0f07-8a28-8395-8f3d-cb6d758965d7.messages.txt" not in included
    assert "session_20260508_004724.log" not in included
    assert "stdout.json" not in included
    assert "stderr.txt" not in included
    assert "pb_artifact_adopt.v0.0.196.json" not in included
    assert "pb_artifact_current.v0.0.196.json" not in included
    assert "pb_artifact_verify.v0.0.196.json" not in included
    assert "pb_src_list.before_adopt.v0.0.196.json" not in included
    assert "pb_test.full.v0.0.196.report.json" not in included
    assert "promptbranch-project-list.json" not in included
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
    registry.initialize()
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
        ".pb_profile/ask_records/req-demo/reply.parsed.json",
        ".pb_profile/ask_protocol_runs/req-demo.json",
        ".pb_profile/release_logs/v0.0.222/pb_ask_protocol_smoke.v0.0.222.json",
        "task_69fd0a71-3cb8-8397-bd09-9be7fcccafe1_message.txt",
        "task_show_69f85be3-db68-838a-b6c8-66a2c7c40be9_messages.txt",
        "task_69fd0f07-8a28-8395-8f3d-cb6d758965d7.messages.txt",
        "session_20260508_004724.log",
        "nested/release.zip",
        "pkg/__pycache__/module.cpython-312.pyc",
        "stdout.json",
        "stderr.txt",
        "pb_artifact_adopt.v0.0.196.json",
        "pb_src_list.before_adopt.v0.0.196.json",
        "pb_test.full.v0.0.196.report.json",
        "promptbranch-project-list.json",
    ]

    bad = release_entry_hygiene_violations(names)

    assert "VERSION" not in bad
    assert "src/app.py" not in bad
    assert ".pb_profile/ask_records/req-demo/reply.parsed.json" in bad
    assert ".pb_profile/ask_protocol_runs/req-demo.json" in bad
    assert ".pb_profile/release_logs/v0.0.222/pb_ask_protocol_smoke.v0.0.222.json" in bad
    assert "task_69fd0a71-3cb8-8397-bd09-9be7fcccafe1_message.txt" in bad
    assert "task_show_69f85be3-db68-838a-b6c8-66a2c7c40be9_messages.txt" in bad
    assert "task_69fd0f07-8a28-8395-8f3d-cb6d758965d7.messages.txt" in bad
    assert "session_20260508_004724.log" in bad
    assert "nested/release.zip" in bad
    assert "pkg/__pycache__/module.cpython-312.pyc" in bad
    assert "stdout.json" in bad
    assert "stderr.txt" in bad
    assert "pb_artifact_adopt.v0.0.196.json" in bad
    assert "pb_src_list.before_adopt.v0.0.196.json" in bad
    assert "pb_test.full.v0.0.196.report.json" in bad
    assert "promptbranch-project-list.json" in bad


def test_verify_zip_artifact_rejects_generated_task_transcript(tmp_path: Path) -> None:
    zip_path = tmp_path / "bad.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("VERSION", "v0.1.0\n")
        archive.writestr("task_69fd0a71-3cb8-8397-bd09-9be7fcccafe1_message.txt", "transcript")

    payload = verify_zip_artifact(zip_path)

    assert payload["ok"] is False
    assert payload["hygiene_violation_count"] == 1
    assert payload["hygiene_violations"] == ["task_69fd0a71-3cb8-8397-bd09-9be7fcccafe1_message.txt"]


def test_verify_zip_artifact_rejects_task_messages_txt_transcript(tmp_path: Path) -> None:
    zip_path = tmp_path / "bad-messages-txt.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("VERSION", "v0.1.0\n")
        archive.writestr("task_69fd0f07-8a28-8395-8f3d-cb6d758965d7.messages.txt", "transcript")

    payload = verify_zip_artifact(zip_path)

    assert payload["ok"] is False
    assert payload["hygiene_violation_count"] == 1
    assert payload["hygiene_violations"] == ["task_69fd0f07-8a28-8395-8f3d-cb6d758965d7.messages.txt"]


def test_artifact_registry_current_is_repo_scoped(tmp_path: Path) -> None:
    registry = ArtifactRegistry(tmp_path / "profile")
    registry.initialize()
    registry.add(ArtifactRecord(
        path=str(tmp_path / "my_awx_v0.0.200.zip"),
        filename="my_awx_v0.0.200.zip",
        kind="adopted_release",
        version="v0.0.200",
        repo_path=None,
        repo_id="my_awx",
        sha256="a" * 64,
        size_bytes=10,
        file_count=2,
        created_at="2026-06-10T10:00:00Z",
    ))
    registry.add(ArtifactRecord(
        path=str(tmp_path / "platform-gitops_v0.0.4.zip"),
        filename="platform-gitops_v0.0.4.zip",
        kind="adopted_release",
        version="v0.0.4",
        repo_path=None,
        repo_id="platform-gitops",
        sha256="b" * 64,
        size_bytes=10,
        file_count=2,
        created_at="2026-06-10T11:00:00Z",
    ))

    assert registry.current(repo_id="my_awx")["filename"] == "my_awx_v0.0.200.zip"
    assert registry.current(repo_id="platform-gitops")["filename"] == "platform-gitops_v0.0.4.zip"


def test_artifact_registry_current_all_groups_by_repo(tmp_path: Path) -> None:
    registry = ArtifactRegistry(tmp_path / "profile")
    registry.initialize()
    registry.add(ArtifactRecord(
        path=str(tmp_path / "my_awx_v0.0.200.zip"),
        filename="my_awx_v0.0.200.zip",
        kind="adopted_release",
        version="v0.0.200",
        repo_path=None,
        repo_id="my_awx",
        sha256="a" * 64,
        size_bytes=10,
        file_count=2,
        created_at="2026-06-10T10:00:00Z",
    ))
    registry.add(ArtifactRecord(
        path=str(tmp_path / "my_awx_v0.0.201.zip"),
        filename="my_awx_v0.0.201.zip",
        kind="adopted_release",
        version="v0.0.201",
        repo_path=None,
        repo_id="my_awx",
        sha256="c" * 64,
        size_bytes=10,
        file_count=2,
        created_at="2026-06-10T12:00:00Z",
    ))
    registry.add(ArtifactRecord(
        path=str(tmp_path / "platform-gitops_v0.0.4.zip"),
        filename="platform-gitops_v0.0.4.zip",
        kind="adopted_release",
        version="v0.0.4",
        repo_path=None,
        repo_id="platform-gitops",
        sha256="b" * 64,
        size_bytes=10,
        file_count=2,
        created_at="2026-06-10T11:00:00Z",
    ))

    current_all = registry.current_all()

    assert current_all["my_awx"]["filename"] == "my_awx_v0.0.201.zip"
    assert current_all["platform-gitops"]["filename"] == "platform-gitops_v0.0.4.zip"


def test_artifact_registry_current_without_repo_rejects_ambiguous_multi_repo_state(tmp_path: Path) -> None:
    registry = ArtifactRegistry(tmp_path / "profile")
    registry.initialize()
    registry.add(ArtifactRecord(
        path=str(tmp_path / "my_awx_v0.0.200.zip"),
        filename="my_awx_v0.0.200.zip",
        kind="adopted_release",
        version="v0.0.200",
        repo_path=None,
        repo_id="my_awx",
        sha256="a" * 64,
        size_bytes=10,
        file_count=2,
        created_at="2026-06-10T10:00:00Z",
    ))
    registry.add(ArtifactRecord(
        path=str(tmp_path / "platform-gitops_v0.0.4.zip"),
        filename="platform-gitops_v0.0.4.zip",
        kind="adopted_release",
        version="v0.0.4",
        repo_path=None,
        repo_id="platform-gitops",
        sha256="b" * 64,
        size_bytes=10,
        file_count=2,
        created_at="2026-06-10T11:00:00Z",
    ))

    assert registry.current() is None
    assert registry.is_current_ambiguous() is True


def test_artifact_registry_single_repo_current_works(tmp_path: Path) -> None:
    registry = ArtifactRegistry(tmp_path / "profile")
    registry.initialize()
    registry.add(ArtifactRecord(
        path=str(tmp_path / "my_awx_v0.0.200.zip"),
        filename="my_awx_v0.0.200.zip",
        kind="adopted_release",
        version="v0.0.200",
        repo_path=None,
        repo_id="my_awx",
        sha256="a" * 64,
        size_bytes=10,
        file_count=2,
        created_at="2026-06-10T10:00:00Z",
    ))

    assert registry.current()["filename"] == "my_awx_v0.0.200.zip"

def test_verify_zip_artifact_allows_portable_promptbranch_repo_manifest(tmp_path: Path) -> None:
    zip_path = tmp_path / "portable.zip"
    manifest = {
        "project_id": "candlecast",
        "project_home_url": "https://chatgpt.com/g/g-p-demo/project",
        "repo_id": "architecture-process",
        "role": "architecture_process",
        "artifact_pattern": "architecture-process_<version>.zip",
    }
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("VERSION", "v0.29.0\n")
        archive.writestr(".promptbranch-repo.json", json.dumps(manifest))
        archive.writestr("README.md", "demo\n")

    payload = verify_zip_artifact(zip_path)

    assert payload["ok"] is True
    assert payload["hygiene_violations"] == []
    assert payload["promptbranch_repo_manifest_violations"] == []


def test_verify_zip_artifact_rejects_promptbranch_repo_manifest_with_local_state(tmp_path: Path) -> None:
    zip_path = tmp_path / "local-state.zip"
    manifest = {
        "project_id": "candlecast",
        "repo_id": "architecture-process",
        "repo_root": "/home/spikkie/git/architecture-process",
        "state_file": "/home/spikkie/git/architecture-process/.pb_profile/.promptbranch_state.json",
        "token": "secret-token",
    }
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("VERSION", "v0.29.0\n")
        archive.writestr(".promptbranch-repo.json", json.dumps(manifest))
        archive.writestr("README.md", "demo\n")

    payload = verify_zip_artifact(zip_path)

    assert payload["ok"] is False
    violations = payload["promptbranch_repo_manifest_violations"]
    assert any(item.endswith(":repo_root:local_absolute_path") for item in violations)
    assert any(item.endswith(":state_file:local_absolute_path") for item in violations)
    assert any(item.endswith(":state_file:local_promptbranch_state_path") for item in violations)
    assert any(item.endswith(":token:sensitive_field") for item in violations)

def test_artifact_registry_rejects_noncanonical_record_on_add(tmp_path: Path) -> None:
    registry = ArtifactRegistry(tmp_path / "profile")
    registry.initialize()

    try:
        registry.add(ArtifactRecord(
            path=str(tmp_path / "demo_1.2.3.zip"),
            filename="demo_1.2.3.zip",
            kind="adopted_release",
            version="1.2.3",
            repo_path=None,
            repo_id="demo",
            sha256="a" * 64,
            size_bytes=1,
            file_count=1,
            created_at="2026-07-14T00:00:00Z",
        ))
    except ValueError as exc:
        assert "canonical <repo_id>_v<version>.zip" in str(exc)
    else:
        raise AssertionError("noncanonical artifact record should be rejected")


def test_artifact_registry_rejects_noncanonical_record_on_load(tmp_path: Path) -> None:
    registry = ArtifactRegistry(tmp_path / "profile")
    registry.profile_dir.mkdir(parents=True)
    registry.path.write_text(json.dumps({
        "schema_version": 1,
        "artifacts": [{
            "path": str(tmp_path / "demo_1.2.3.zip"),
            "filename": "demo_1.2.3.zip",
            "kind": "adopted_release",
            "version": "1.2.3",
            "repo_path": None,
            "repo_id": "demo",
            "sha256": "a" * 64,
            "size_bytes": 1,
            "file_count": 1,
            "created_at": "2026-07-14T00:00:00Z",
        }],
    }), encoding="utf-8")

    state = registry.inspect()

    assert state["ok"] is False
    assert state["status"] == "artifact_registry_invalid"
    assert "canonical <repo_id>_v<version>.zip" in state["error"]



def test_artifact_mutation_remains_blocked_when_registry_missing(tmp_path: Path) -> None:
    import pytest
    from promptbranch_artifacts import ArtifactRegistryStateError

    registry = ArtifactRegistry(tmp_path / ".pb_profile")
    record = ArtifactRecord(
        path=str(tmp_path / "repo_v1.0.0.zip"),
        filename="repo_v1.0.0.zip",
        kind="release",
        version="v1.0.0",
        repo_path=str(tmp_path),
        repo_id="repo",
        sha256="0" * 64,
        size_bytes=1,
        file_count=1,
        created_at="2026-07-15T00:00:00Z",
        source_ref="repo_v1.0.0.zip",
    )

    with pytest.raises(ArtifactRegistryStateError) as exc_info:
        registry.add(record)

    assert exc_info.value.status == "artifact_registry_missing"
    assert not registry.path.exists()


def test_artifact_mutation_remains_blocked_when_registry_invalid(tmp_path: Path) -> None:
    import pytest
    from promptbranch_artifacts import ArtifactRegistryStateError

    registry = ArtifactRegistry(tmp_path / ".pb_profile")
    registry.profile_dir.mkdir(parents=True)
    registry.path.write_text("{broken", encoding="utf-8")
    record = ArtifactRecord(
        path=str(tmp_path / "repo_v1.0.0.zip"),
        filename="repo_v1.0.0.zip",
        kind="release",
        version="v1.0.0",
        repo_path=str(tmp_path),
        repo_id="repo",
        sha256="0" * 64,
        size_bytes=1,
        file_count=1,
        created_at="2026-07-15T00:00:00Z",
        source_ref="repo_v1.0.0.zip",
    )

    with pytest.raises(ArtifactRegistryStateError) as exc_info:
        registry.add(record)

    assert exc_info.value.status == "artifact_registry_invalid"


def test_artifact_registry_rejects_partial_project_source_identity_evidence(tmp_path: Path) -> None:
    registry = ArtifactRegistry(tmp_path / "profile")
    registry.initialize()
    record = ArtifactRecord(
        path=str(tmp_path / "demo_v1.2.3.zip"),
        filename="demo_v1.2.3.zip",
        kind="adopted_release",
        version="v1.2.3",
        repo_path=None,
        repo_id="demo",
        sha256="a" * 64,
        size_bytes=1,
        file_count=1,
        created_at="2026-07-16T00:00:00Z",
        source_ref="demo_v1.2.3(1).zip",
        project_url="https://chatgpt.com/g/g-p-demo/project",
        source_requested_ref="demo_v1.2.3.zip",
        source_processed_file_id="file_123",
        source_library_metadata_object_id=None,
    )

    try:
        registry.add(record)
    except ValueError as exc:
        assert "source_library_metadata_object_id" in str(exc)
    else:
        raise AssertionError("partial Project Source identity evidence should be rejected")


def test_repo_snapshot_includes_tracked_project_binding(tmp_path: Path) -> None:
    repo = tmp_path / "demo-repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.3\n", encoding="utf-8")
    (repo / ".not_to_zip").write_text("*.log\n", encoding="utf-8")
    (repo / ".promptbranch-repo.json").write_text(json.dumps({
        "schema_version": 1,
        "project_id": "g-p-demo-project",
        "project_home_url": "https://chatgpt.com/g/g-p-demo-project/project",
        "repo_id": "demo-repo",
        "artifact_pattern": "demo-repo_<version>.zip",
        "role": "release_authority",
    }), encoding="utf-8")
    (repo / "README.md").write_text("demo\n", encoding="utf-8")

    record, entries = create_repo_snapshot(repo, output_dir=tmp_path / "out")

    assert ".promptbranch-repo.json" in entries
    with zipfile.ZipFile(record.path) as archive:
        assert ".promptbranch-repo.json" in archive.namelist()
    assert verify_zip_artifact(record.path)["ok"] is True


def test_adopted_release_version_hash_is_immutable(tmp_path: Path) -> None:
    registry = ArtifactRegistry(tmp_path / "profile")
    registry.initialize()
    first = ArtifactRecord(path=str(tmp_path / "demo_v1.2.3.zip"), filename="demo_v1.2.3.zip", kind="adopted_release", version="v1.2.3", repo_path=None, repo_id="demo", sha256="a" * 64, size_bytes=1, file_count=1, created_at="2026-08-02T00:00:00Z")
    registry.add(first)
    second = ArtifactRecord(path=str(tmp_path / "other" / "demo_v1.2.3.zip"), filename="demo_v1.2.3.zip", kind="adopted_release", version="v1.2.3", repo_path=None, repo_id="demo", sha256="b" * 64, size_bytes=1, file_count=1, created_at="2026-08-02T00:01:00Z")
    import pytest
    with pytest.raises(ArtifactIdentityConflictError):
        registry.add(second)
