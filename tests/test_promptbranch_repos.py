
from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

from promptbranch_artifacts import ArtifactRecord, ArtifactRegistry, sha256_file
from promptbranch_cli import ProjectRegistryResolutionError, _artifact_current_payload, _artifact_registry_from_args, _repo_doctor_payload, _repo_list_payload, build_backend, make_parser
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
    normalized_version = version if version.startswith("v") else f"v{version}"
    filename = f"{repo_id}_{normalized_version}.zip"
    source = project_dir / filename
    source.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("VERSION", normalized_version + "\n")
        archive.writestr("README.md", f"{repo_id} {normalized_version}\n")
    verification_sha = sha256_file(source)
    registered = registry.add(ArtifactRecord(
        path=str(source),
        filename=filename,
        kind="adopted_release",
        version=normalized_version,
        repo_path=None,
        repo_id=repo_id,
        sha256=verification_sha,
        size_bytes=source.stat().st_size,
        file_count=2,
        created_at=f"2026-06-10T10:00:0{len(registry.list())}Z",
        source_ref=filename,
        project_url=PROJECT_URL,
    ))
    assert Path(str(registered["path"])).is_file()
    ConversationStateStore(str(project_dir)).remember_artifact(
        project_url=PROJECT_URL,
        artifact_ref=filename,
        artifact_version=normalized_version,
        source_ref=filename,
        source_version=normalized_version,
        repo_id=repo_id,
    )


def _backend_args(profile_dir: Path, *, explicit_profile_dir: bool) -> argparse.Namespace:
    return argparse.Namespace(
        service_base_url="http://localhost:8000",
        service_token=None,
        service_timeout_seconds=30.0,
        project_url=PROJECT_URL,
        email=None,
        password=None,
        password_file=None,
        profile_dir=str(profile_dir),
        headless=True,
        use_playwright=False,
        browser_channel=None,
        enable_fedcm=False,
        keep_no_sandbox=False,
        max_retries=1,
        retry_backoff_seconds=0.1,
        debug_browser=False,
        debug=False,
        slow_mo_ms=0,
        _profile_dir_explicit=explicit_profile_dir,
    )


def test_build_backend_reads_project_scoped_state_from_joined_repo(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", str(tmp_path / "config"))
    repo = _join_repo(tmp_path, "my_awx", "consumer")
    project_dir = project_registry_dir("kubernetes")
    repo_profile = repo / ".pb_profile"
    project_conversation = f"{PROJECT_URL[:-len('/project')]}/c/project-selected"
    stale_repo_conversation = f"{PROJECT_URL[:-len('/project')]}/c/stale-repo-local"
    ConversationStateStore(str(project_dir)).remember(PROJECT_URL, project_conversation, project_name="kubernetes")
    ConversationStateStore(str(project_dir)).remember_artifact(
        project_url=PROJECT_URL,
        artifact_ref="my_awx_v0.0.212.4.zip",
        artifact_version="v0.0.212.4",
        source_ref="my_awx_v0.0.212.4.zip",
        source_version="v0.0.212.4",
        repo_id="my_awx",
    )
    ConversationStateStore(str(repo_profile)).remember(PROJECT_URL, stale_repo_conversation, project_name="kubernetes")
    ConversationStateStore(str(repo_profile)).remember_artifact(
        project_url=PROJECT_URL,
        artifact_ref="my_awx_v0.0.200.8.zip",
        artifact_version="v0.0.200.8",
        source_ref="my_awx_v0.0.200.8.zip",
        source_version="v0.0.200.8",
        repo_id="my_awx",
    )
    monkeypatch.chdir(repo)

    args = _backend_args(repo_profile, explicit_profile_dir=False)
    backend = build_backend(args)
    snapshot = backend.state_snapshot()

    assert snapshot["state_file"] == str(project_dir / ".promptbranch_state.json")
    assert snapshot["conversation_url"] == project_conversation
    assert snapshot["conversation_id"] == "project-selected"
    assert snapshot["artifact_ref"] == "my_awx_v0.0.212.4.zip"
    assert args.profile_dir == str(repo_profile.resolve())


def test_build_backend_explicit_profile_dir_keeps_profile_state_override(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", str(tmp_path / "config"))
    repo = _join_repo(tmp_path, "my_awx", "consumer")
    project_dir = project_registry_dir("kubernetes")
    explicit_profile = tmp_path / "explicit-profile"
    project_conversation = f"{PROJECT_URL[:-len('/project')]}/c/project-selected"
    explicit_conversation = f"{PROJECT_URL[:-len('/project')]}/c/explicit-profile-selected"
    ConversationStateStore(str(project_dir)).remember(PROJECT_URL, project_conversation, project_name="kubernetes")
    ConversationStateStore(str(explicit_profile)).remember(PROJECT_URL, explicit_conversation, project_name="kubernetes")
    monkeypatch.chdir(repo)

    backend = build_backend(_backend_args(explicit_profile, explicit_profile_dir=True))
    snapshot = backend.state_snapshot()

    assert snapshot["state_file"] == str(explicit_profile / ".promptbranch_state.json")
    assert snapshot["conversation_url"] == explicit_conversation
    assert snapshot["conversation_id"] == "explicit-profile-selected"


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
    assert by_repo["my_awx"]["current_artifact"] == "my_awx_v0.0.200.zip"
    assert by_repo["platform-gitops"]["current_artifact"] == "platform-gitops_v0.0.3.zip"


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
    assert payload["repos"]["my_awx"]["state"]["artifact_ref"] == "my_awx_v0.0.200.zip"
    assert payload["repos"]["my_gitlab"]["state"]["artifact_ref"] == "my_gitlab_v0.0.14.zip"


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
    assert payload["repos"]["does-not-exist"]["state"] is None
    assert payload["repos"]["does-not-exist"]["registry_current"] is None


def test_default_resolved_profile_dir_does_not_disable_project_registry(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", str(tmp_path / "config"))
    repo = _join_repo(tmp_path, "my_awx", "consumer")
    legacy_profile = repo / ".pb_profile"
    monkeypatch.chdir(repo)

    registry = _artifact_registry_from_args(argparse.Namespace(profile_dir=str(legacy_profile), _profile_dir_explicit=False))

    assert registry.path == project_registry_dir("kubernetes") / "promptbranch_artifacts.json"


def test_explicit_profile_dir_cannot_override_project_registry(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", str(tmp_path / "config"))
    repo = _join_repo(tmp_path, "my_awx", "consumer")
    explicit_profile = tmp_path / "explicit-profile"
    monkeypatch.chdir(repo)

    registry = _artifact_registry_from_args(argparse.Namespace(profile_dir=str(explicit_profile), _profile_dir_explicit=True))

    assert registry.path == project_registry_dir("kubernetes") / "promptbranch_artifacts.json"
    assert not (explicit_profile / "promptbranch_artifacts.json").exists()


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
    assert payload["repos"]["platform-gitops"]["state"]["artifact_ref"] == "platform-gitops_v0.0.3.zip"


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


def test_artifact_registry_resolution_requires_identity_manifest(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", str(tmp_path / "config"))
    repo = tmp_path / "unjoined"
    repo.mkdir()
    monkeypatch.chdir(repo)

    try:
        _artifact_registry_from_args(argparse.Namespace(profile_dir=str(repo / ".pb_profile"), _profile_dir_explicit=False))
    except ProjectRegistryResolutionError as exc:
        payload = exc.payload
    else:
        raise AssertionError("project registry resolution should fail")

    assert payload["status"] == "project_scope_unresolved"
    assert payload["registry_source"] == "unresolved"
    assert payload["fallback_used"] is False
    assert payload["missing_repo_count"] is None
    assert not (repo / ".pb_profile" / "promptbranch_artifacts.json").exists()


def test_artifact_registry_resolution_rejects_missing_project_registry(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", str(tmp_path / "config"))
    repo = _join_repo(tmp_path, "my_awx", "consumer")
    registry_file = project_registry_dir("kubernetes") / "promptbranch_artifacts.json"
    registry_file.unlink()
    monkeypatch.chdir(repo)

    try:
        _artifact_registry_from_args(argparse.Namespace(profile_dir=str(repo / ".pb_profile"), _profile_dir_explicit=False))
    except ProjectRegistryResolutionError as exc:
        payload = exc.payload
    else:
        raise AssertionError("missing registry should fail")

    assert payload["status"] == "artifact_registry_missing"
    assert payload["registry_source"] == "project_registry"
    assert payload["registry_exists"] is False
    assert payload["registry_valid"] is False
    assert payload["project_id"] == "kubernetes"
    assert payload["repo_id"] == "my_awx"
    assert payload["fallback_used"] is False


def test_artifact_registry_resolution_rejects_invalid_project_registry(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", str(tmp_path / "config"))
    repo = _join_repo(tmp_path, "my_awx", "consumer")
    registry_file = project_registry_dir("kubernetes") / "promptbranch_artifacts.json"
    registry_file.write_text("{invalid", encoding="utf-8")
    monkeypatch.chdir(repo)

    try:
        _artifact_registry_from_args(argparse.Namespace(profile_dir=None, _profile_dir_explicit=False))
    except ProjectRegistryResolutionError as exc:
        payload = exc.payload
    else:
        raise AssertionError("invalid registry should fail")

    assert payload["status"] == "artifact_registry_invalid"
    assert payload["registry_exists"] is True
    assert payload["registry_valid"] is False
    assert payload["registry_readable"] is True



def test_artifact_registry_resolution_rejects_unreadable_project_registry(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", str(tmp_path / "config"))
    repo = _join_repo(tmp_path, "my_awx", "consumer")
    registry_file = project_registry_dir("kubernetes") / "promptbranch_artifacts.json"
    original_read_text = Path.read_text

    def unreadable(self: Path, *args, **kwargs):
        if self == registry_file:
            raise PermissionError("denied for test")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", unreadable)
    monkeypatch.chdir(repo)

    try:
        _artifact_registry_from_args(argparse.Namespace(profile_dir=None, _profile_dir_explicit=False))
    except ProjectRegistryResolutionError as exc:
        payload = exc.payload
    else:
        raise AssertionError("unreadable registry should fail")

    assert payload["status"] == "artifact_registry_unreadable"
    assert payload["registry_exists"] is True
    assert payload["registry_valid"] is False
    assert payload["registry_readable"] is False


def test_artifact_registry_resolution_rejects_repo_local_registry(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", str(tmp_path / "config"))
    repo = _join_repo(tmp_path, "my_awx", "consumer")
    legacy = repo / ".pb_profile" / "promptbranch_artifacts.json"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text(json.dumps({"schema_version": 1, "artifacts": []}), encoding="utf-8")
    monkeypatch.chdir(repo)

    try:
        _artifact_registry_from_args(argparse.Namespace(profile_dir=None, _profile_dir_explicit=False))
    except ProjectRegistryResolutionError as exc:
        payload = exc.payload
    else:
        raise AssertionError("obsolete repo-local registry should fail")

    assert payload["status"] == "legacy_repo_local_registry_detected"
    assert payload["fallback_used"] is False
    assert payload["missing_repo_count"] is None

def test_artifact_current_missing_registry_is_not_empty_success(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", str(tmp_path / "config"))
    repo = _join_repo(tmp_path, "my_awx", "consumer")
    project_dir = project_registry_dir("kubernetes")
    (project_dir / "promptbranch_artifacts.json").unlink()
    monkeypatch.chdir(repo)

    payload = _artifact_current_payload(None, ArtifactRegistry(project_dir), all_repos=True, state_store=ConversationStateStore(str(project_dir)))

    assert payload["ok"] is False
    assert payload["status"] == "artifact_registry_missing"
    assert payload["repo_count"] is None
    assert payload["missing_repo_count"] is None
    assert payload["registry_exists"] is False


def test_repo_doctor_reports_legacy_repo_local_registry(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", str(tmp_path / "config"))
    repo = _join_repo(tmp_path, "my_awx", "consumer")
    _add_current(project_registry_dir("kubernetes"), "my_awx", "0.0.200")
    legacy = repo / ".pb_profile" / "promptbranch_artifacts.json"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text(json.dumps({"schema_version": 1, "artifacts": []}), encoding="utf-8")
    monkeypatch.chdir(repo)

    payload = _repo_doctor_payload(argparse.Namespace(profile_dir=None))

    assert payload["ok"] is False
    checks = {item["id"]: item for item in payload["checks"]}
    assert checks["legacy_repo_local_registries_absent"]["status"] == "failed"
    assert checks["legacy_repo_local_registries_absent"]["details"]["legacy_registry_repos"] == ["my_awx"]


def test_legacy_registry_import_command_is_removed() -> None:
    parser = make_parser()
    project_parser = next(action for action in parser._actions if getattr(action, "dest", None) == "command").choices["project"]
    project_commands = next(action for action in project_parser._actions if getattr(action, "dest", None) == "project_command").choices
    assert "import-current-registry" not in project_commands
