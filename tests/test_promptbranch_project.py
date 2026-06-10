
from __future__ import annotations

import json
from pathlib import Path

from promptbranch_project import load_repo_identity, project_registry_dir, project_repo_config_path, write_repo_identity, join_local_repo


def test_project_registry_path_is_derived_from_project_id(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    assert project_registry_dir("kubernetes") == tmp_path / "state" / "kubernetes"


def test_project_join_identity_and_local_registry(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", str(tmp_path / "config"))
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
