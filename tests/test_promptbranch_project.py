
from __future__ import annotations

import json
from pathlib import Path

from promptbranch_project import load_repo_identity, project_registry_dir, project_registry_file, project_repo_config_path, write_repo_identity, join_local_repo


def test_project_registry_path_is_derived_from_project_id(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    assert project_registry_dir("kubernetes") == tmp_path / "state" / "kubernetes"


def test_project_join_identity_and_local_registry(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    repo = tmp_path / "my_awx"
    path = write_repo_identity(
        repo,
        project_id="kubernetes",
        project_home_url="https://chatgpt.com/g/g-p-demo-kubernetes/project",
        repo_id="my_awx",
        artifact_pattern="my_awx_<version>.zip",
        role="consumer",
    )
    identity = load_repo_identity(repo)
    assert identity is not None
    assert path.name == ".promptbranch-repo.json"
    assert identity.project_id == "kubernetes"
    assert identity.repo_id == "my_awx"
    registry = join_local_repo(identity)
    payload = json.loads(registry.read_text(encoding="utf-8"))
    assert payload["repos"]["my_awx"]["repo_root"] == str(repo.resolve())
    assert project_repo_config_path("kubernetes") == registry
    registry_file = project_registry_file("kubernetes")
    assert registry_file.is_file()
    assert json.loads(registry_file.read_text(encoding="utf-8"))["artifacts"] == []

from promptbranch_artifacts import ArtifactRecord, ArtifactRegistry
from promptbranch_project import import_current_registry
from promptbranch_state import ConversationStateStore


def _add_legacy_current(profile_dir: Path, repo_id: str, version: str, project_url: str = "https://chatgpt.com/g/g-p-demo-kubernetes/project") -> None:
    registry = ArtifactRegistry(profile_dir)
    filename = f"{repo_id}_{version}.zip"
    registry.add(ArtifactRecord(
        path=str(profile_dir.parent / filename),
        filename=filename,
        kind="adopted_release",
        version=version,
        repo_path=None,
        repo_id=repo_id,
        sha256=(repo_id[0] if repo_id else "a") * 64,
        size_bytes=1,
        file_count=1,
        created_at="2026-06-11T08:00:00Z",
        source_ref=filename,
        project_url=project_url,
    ))
    ConversationStateStore(str(profile_dir)).remember_artifact(
        project_url=project_url,
        artifact_ref=filename,
        artifact_version=version,
        source_ref=filename,
        source_version=version,
        repo_id=repo_id,
    )


def test_project_import_current_registry_dry_run_does_not_mutate(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    repo = tmp_path / "my_awx"
    legacy_profile = repo / ".pb_profile"
    path = write_repo_identity(
        repo,
        project_id="kubernetes",
        project_home_url="https://chatgpt.com/g/g-p-demo-kubernetes/project",
        repo_id="my_awx",
        artifact_pattern="my_awx_<version>.zip",
        role="consumer",
    )
    identity = load_repo_identity(repo)
    assert identity is not None
    join_local_repo(identity)
    _add_legacy_current(legacy_profile, "my_awx", "0.0.200")

    payload = import_current_registry(identity, dry_run=True)

    assert payload["ok"] is True
    assert payload["status"] == "import_plan"
    assert payload["planned_import_count"] == 1
    assert payload["mutated"] is False
    assert ArtifactRegistry(project_registry_dir("kubernetes")).current(repo_id="my_awx") is None


def test_project_import_current_registry_imports_artifacts_and_state(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    repo = tmp_path / "my_awx"
    legacy_profile = repo / ".pb_profile"
    write_repo_identity(
        repo,
        project_id="kubernetes",
        project_home_url="https://chatgpt.com/g/g-p-demo-kubernetes/project",
        repo_id="my_awx",
        artifact_pattern="my_awx_<version>.zip",
        role="consumer",
    )
    identity = load_repo_identity(repo)
    assert identity is not None
    join_local_repo(identity)
    _add_legacy_current(legacy_profile, "my_awx", "0.0.200")

    payload = import_current_registry(identity)

    assert payload["ok"] is True
    assert payload["status"] == "imported"
    assert payload["imported_count"] == 1
    project_dir = project_registry_dir("kubernetes")
    assert ArtifactRegistry(project_dir).current(repo_id="my_awx")["filename"] == "my_awx_0.0.200.zip"
    snapshot = ConversationStateStore(str(project_dir)).snapshot("https://chatgpt.com/g/g-p-demo-kubernetes/project", repo_id="my_awx")
    assert snapshot["artifact_ref"] == "my_awx_0.0.200.zip"
    assert snapshot["source_ref"] == "my_awx_0.0.200.zip"


def test_project_import_current_registry_conflicts_fail_closed(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    repo = tmp_path / "my_awx"
    legacy_profile = repo / ".pb_profile"
    write_repo_identity(
        repo,
        project_id="kubernetes",
        project_home_url="https://chatgpt.com/g/g-p-demo-kubernetes/project",
        repo_id="my_awx",
        artifact_pattern="my_awx_<version>.zip",
        role="consumer",
    )
    identity = load_repo_identity(repo)
    assert identity is not None
    join_local_repo(identity)
    _add_legacy_current(legacy_profile, "my_awx", "0.0.201")
    _add_legacy_current(project_registry_dir("kubernetes"), "my_awx", "0.0.200")

    payload = import_current_registry(identity)

    assert payload["ok"] is False
    assert payload["status"] == "import_conflicts_found"
    assert payload["conflict_count"] == 1
    assert ArtifactRegistry(project_registry_dir("kubernetes")).current(repo_id="my_awx")["filename"] == "my_awx_0.0.200.zip"
