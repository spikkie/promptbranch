
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from promptbranch_project import load_repo_identity, project_registry_dir, project_registry_file, project_repo_config_path, repo_identity_mismatches, validate_tracked_repo_identity, write_repo_identity, join_local_repo


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


def _tracked_binding(repo: Path) -> dict[str, object]:
    return {
        "schema_version": 1,
        "project_id": "g-p-demo-project",
        "project_home_url": "https://chatgpt.com/g/g-p-demo-project/project",
        "repo_id": "demo-repo",
        "artifact_pattern": "demo-repo_<version>.zip",
        "role": "release_authority",
    }


def test_project_join_recreates_local_state_from_tracked_binding(tmp_path: Path) -> None:
    repo = tmp_path / "demo-repo"
    repo.mkdir()
    (repo / ".promptbranch-repo.json").write_text(json.dumps(_tracked_binding(repo)), encoding="utf-8")
    env = os.environ.copy()
    env["PROMPTBRANCH_PROJECT_CONFIG_HOME"] = str(tmp_path / "config")
    env["PROMPTBRANCH_PROJECT_STATE_HOME"] = str(tmp_path / "state")

    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parents[1] / "promptbranch_cli.py"), "project", "join", "--repo-root", str(repo), "--json"],
        cwd=repo, env=env, text=True, capture_output=True, check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["binding_source"] == "tracked_repository_file"
    assert payload["binding_created"] is False
    assert Path(payload["local_repo_config_file"]).is_file()
    assert Path(payload["registry_file"]).is_file()


def test_project_join_refuses_argument_mismatch_with_tracked_binding(tmp_path: Path) -> None:
    repo = tmp_path / "demo-repo"
    repo.mkdir()
    binding_path = repo / ".promptbranch-repo.json"
    original = json.dumps(_tracked_binding(repo), indent=2) + "\n"
    binding_path.write_text(original, encoding="utf-8")
    env = os.environ.copy()
    env["PROMPTBRANCH_PROJECT_CONFIG_HOME"] = str(tmp_path / "config")
    env["PROMPTBRANCH_PROJECT_STATE_HOME"] = str(tmp_path / "state")

    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parents[1] / "promptbranch_cli.py"), "project", "join", "--repo-root", str(repo), "--project-id", "wrong-project", "--json"],
        cwd=repo, env=env, text=True, capture_output=True, check=False,
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert "tracked project binding mismatch" in payload["error"]
    assert binding_path.read_text(encoding="utf-8") == original
    assert not (tmp_path / "config").exists()


def test_accidental_binding_deletion_is_recoverable_from_git(tmp_path: Path) -> None:
    if shutil.which("git") is None:
        return
    repo = tmp_path / "demo-repo"
    repo.mkdir()
    binding_path = repo / ".promptbranch-repo.json"
    binding_path.write_text(json.dumps(_tracked_binding(repo), indent=2) + "\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Promptbranch Test"], cwd=repo, check=True)
    subprocess.run(["git", "add", ".promptbranch-repo.json"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "track binding"], cwd=repo, check=True)

    binding_path.unlink()
    assert not binding_path.exists()
    subprocess.run(["git", "restore", ".promptbranch-repo.json"], cwd=repo, check=True)

    assert binding_path.is_file()
    assert validate_tracked_repo_identity(repo, expected_repo_id="demo-repo") == []


def test_tracked_binding_comparison_reports_only_explicit_mismatches(tmp_path: Path) -> None:
    repo = tmp_path / "demo-repo"
    path = write_repo_identity(
        repo, project_id="g-p-demo-project", project_home_url="https://chatgpt.com/g/g-p-demo-project/project",
        repo_id="demo-repo", artifact_pattern="demo-repo_<version>.zip", role="release_authority",
    )
    identity = load_repo_identity(repo)
    assert identity is not None and path.is_file()
    assert repo_identity_mismatches(identity) == []
    assert any("repo_id" in item for item in repo_identity_mismatches(identity, repo_id="wrong"))
