
from __future__ import annotations

import argparse
import json
from pathlib import Path

from promptbranch_artifacts import ArtifactRecord, ArtifactRegistry
from promptbranch_cli import _artifact_current_payload, _artifact_registry_from_args, _repo_doctor_payload, _repo_list_payload
from promptbranch_project import load_repo_identity, project_registry_dir, write_repo_identity, join_local_repo
from promptbranch_state import ConversationStateStore

PROJECT_URL = "https://chatgpt.com/g/g-p-demo-kubernetes/project"


def _join_repo(tmp_path: Path, repo_id: str, role: str = "member") -> Path:
    repo = tmp_path / repo_id
    write_repo_identity(
        repo,
        project_id="kubernetes",
        project_home_url=PROJECT_URL,
        repo_id=repo_id,
        artifact_pattern=f"{repo_id}_<version>.zip",
        role=role,
    )
    identity = load_repo_identity(repo)
    assert identity is not None
    join_local_repo(identity)
    return repo


def _add_current(project_dir: Path, repo_id: str, version: str) -> None:
    registry = ArtifactRegistry(project_dir)
    filename = f"{repo_id}_{version}.zip"
    registry.add(ArtifactRecord(
        path=str(project_dir / filename),
        filename=filename,
        kind="adopted_release",
        version=version,
        repo_path=None,
        repo_id=repo_id,
        sha256="a" * 64,
        size_bytes=1,
        file_count=1,
        created_at=f"2026-06-10T10:00:0{len(registry.list())}Z",
        source_ref=filename,
        project_url=PROJECT_URL,
    ))
    ConversationStateStore(str(project_dir)).remember_artifact(
        project_url=PROJECT_URL,
        artifact_ref=filename,
        artifact_version=version,
        source_ref=filename,
        source_version=version,
        repo_id=repo_id,
    )


def test_repo_list_uses_project_registry_from_any_joined_repo(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", str(tmp_path / "config"))
    my_awx = _join_repo(tmp_path, "my_awx", "consumer")
    platform = _join_repo(tmp_path, "platform-gitops", "deployment_dependency")
    project_dir = project_registry_dir("kubernetes")
    _add_current(project_dir, "my_awx", "0.0.200")
    _add_current(project_dir, "platform-gitops", "0.0.3")
    monkeypatch.chdir(platform)

    payload = _repo_list_payload(argparse.Namespace(profile_dir=None))

    assert payload["ok"] is True
    assert payload["project_id"] == "kubernetes"
    assert payload["registry_file"] == str(project_dir / "promptbranch_artifacts.json")
    by_repo = {item["repo_id"]: item for item in payload["repos"]}
    assert by_repo["my_awx"]["current_artifact"] == "my_awx_0.0.200.zip"
    assert by_repo["platform-gitops"]["current_artifact"] == "platform-gitops_0.0.3.zip"


def test_artifact_current_all_works_from_any_joined_repo(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", str(tmp_path / "config"))
    my_awx = _join_repo(tmp_path, "my_awx", "consumer")
    my_gitlab = _join_repo(tmp_path, "my_gitlab", "platform_component")
    project_dir = project_registry_dir("kubernetes")
    _add_current(project_dir, "my_awx", "0.0.200")
    _add_current(project_dir, "my_gitlab", "0.0.14")
    monkeypatch.chdir(my_gitlab)

    payload = _artifact_current_payload(
        None,
        ArtifactRegistry(project_dir),
        all_repos=True,
        state_store=ConversationStateStore(str(project_dir)),
    )

    assert payload["ok"] is True
    assert payload["scope"]["kind"] == "project"
    assert payload["scope"]["project_id"] == "kubernetes"
    assert payload["repo_count"] == 2
    assert payload["repos"]["my_awx"]["state"]["artifact_ref"] == "my_awx_0.0.200.zip"
    assert payload["repos"]["my_gitlab"]["state"]["artifact_ref"] == "my_gitlab_0.0.14.zip"


def test_repo_doctor_detects_missing_current(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", str(tmp_path / "config"))
    my_awx = _join_repo(tmp_path, "my_awx", "consumer")
    _join_repo(tmp_path, "platform-gitops", "deployment_dependency")
    _add_current(project_registry_dir("kubernetes"), "my_awx", "0.0.200")
    monkeypatch.chdir(my_awx)

    payload = _repo_doctor_payload(argparse.Namespace(profile_dir=None))

    assert payload["ok"] is False
    check = {item["id"]: item for item in payload["checks"]}["configured_repos_have_current_artifact"]
    assert check["status"] == "failed"
    assert "platform-gitops" in check["details"]["missing_current_artifact"]


def test_missing_repo_lookup_still_fails_closed(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    repo = _join_repo(tmp_path, "my_awx", "consumer")
    project_dir = project_registry_dir("kubernetes")
    _add_current(project_dir, "my_awx", "0.0.200")
    monkeypatch.chdir(repo)

    payload = _artifact_current_payload(
        None,
        ArtifactRegistry(project_dir),
        repo_id="does-not-exist",
        state_store=ConversationStateStore(str(project_dir)),
    )

    assert payload["ok"] is False
    assert payload["status"] == "repo_current_not_found"
    assert payload["state"] is None
    assert payload["registry_current"] is None


def test_default_resolved_profile_dir_does_not_disable_project_registry(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", str(tmp_path / "config"))
    repo = _join_repo(tmp_path, "my_awx", "consumer")
    legacy_profile = repo / ".pb_profile"
    monkeypatch.chdir(repo)

    registry = _artifact_registry_from_args(argparse.Namespace(profile_dir=str(legacy_profile), _profile_dir_explicit=False))

    assert registry.path == project_registry_dir("kubernetes") / "promptbranch_artifacts.json"


def test_explicit_profile_dir_still_overrides_project_registry(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", str(tmp_path / "config"))
    repo = _join_repo(tmp_path, "my_awx", "consumer")
    explicit_profile = tmp_path / "explicit-profile"
    monkeypatch.chdir(repo)

    registry = _artifact_registry_from_args(argparse.Namespace(profile_dir=str(explicit_profile), _profile_dir_explicit=True))

    assert registry.path == explicit_profile / "promptbranch_artifacts.json"


def test_artifact_current_all_uses_configured_repos_when_project_registry_empty(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", str(tmp_path / "config"))
    repo = _join_repo(tmp_path, "my_awx", "consumer")
    _join_repo(tmp_path, "platform-gitops", "deployment_dependency")
    project_dir = project_registry_dir("kubernetes")
    monkeypatch.chdir(repo)

    payload = _artifact_current_payload(
        None,
        ArtifactRegistry(project_dir),
        all_repos=True,
        state_store=ConversationStateStore(str(project_dir)),
    )

    assert payload["ok"] is True
    assert payload["registry_file"] == str(project_dir / "promptbranch_artifacts.json")
    assert payload["repo_count"] == 2
    assert payload["repos"]["my_awx"]["status"] == "repo_current_not_found"
    assert payload["repos"]["platform-gitops"]["status"] == "repo_current_not_found"


def test_joined_project_artifact_current_defaults_to_repo_loop_for_one_repo(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", str(tmp_path / "config"))
    repo = _join_repo(tmp_path, "chatgpt_claudecode_workflow-2", "member")
    project_dir = project_registry_dir("kubernetes")
    _add_current(project_dir, "chatgpt_claudecode_workflow-2", "v0.1.75")
    monkeypatch.chdir(repo)

    payload = _artifact_current_payload(
        None,
        ArtifactRegistry(project_dir),
        state_store=ConversationStateStore(str(project_dir)),
    )

    assert payload["ok"] is True
    assert payload["action"] == "artifact_current_all"
    assert payload["scope"]["kind"] == "project"
    assert payload["repo_count"] == 1
    assert list(payload["repos"]) == ["chatgpt_claudecode_workflow-2"]
    current = payload["repos"]["chatgpt_claudecode_workflow-2"]
    assert current["state"]["artifact_ref"] == "chatgpt_claudecode_workflow-2_v0.1.75.zip"


def test_joined_project_artifact_current_repo_filter_keeps_repo_loop_shape(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", str(tmp_path / "config"))
    repo = _join_repo(tmp_path, "my_awx", "consumer")
    _join_repo(tmp_path, "platform-gitops", "deployment_dependency")
    project_dir = project_registry_dir("kubernetes")
    _add_current(project_dir, "my_awx", "0.0.200")
    _add_current(project_dir, "platform-gitops", "0.0.3")
    monkeypatch.chdir(repo)

    payload = _artifact_current_payload(
        None,
        ArtifactRegistry(project_dir),
        repo_id="platform-gitops",
        state_store=ConversationStateStore(str(project_dir)),
    )

    assert payload["ok"] is True
    assert payload["action"] == "artifact_current_all"
    assert payload["scope"]["repo_filter"] == "platform-gitops"
    assert payload["repo_count"] == 1
    assert list(payload["repos"]) == ["platform-gitops"]
    assert payload["repos"]["platform-gitops"]["state"]["artifact_ref"] == "platform-gitops_0.0.3.zip"


def test_project_status_uses_same_repo_loop_management_payload(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", str(tmp_path / "config"))
    repo = _join_repo(tmp_path, "my_awx", "consumer")
    _join_repo(tmp_path, "platform-gitops", "deployment_dependency")
    project_dir = project_registry_dir("kubernetes")
    _add_current(project_dir, "my_awx", "0.0.200")
    _add_current(project_dir, "platform-gitops", "0.0.3")
    monkeypatch.chdir(repo)

    from promptbranch_cli import _current_project_identity_payload, _repo_list_payload

    identity_payload = _current_project_identity_payload(argparse.Namespace(profile_dir=None))
    repo_payload = _repo_list_payload(argparse.Namespace(profile_dir=None))

    assert identity_payload["ok"] is True
    assert repo_payload["repo_count"] == 2
    assert {item["repo_id"] for item in repo_payload["repos"]} == {"my_awx", "platform-gitops"}
