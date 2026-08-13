from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from promptbranch_artifacts import ArtifactRecord, ArtifactRegistry, sha256_file, utc_now
from promptbranch_project import project_registry_dir, write_repo_identity
from promptbranch_skill_sync import sync_skills

REPO = Path(__file__).resolve().parents[1]
SOURCE_VERSION = "v0.1.128.2.5"
REPO_ID = "chatgpt_claudecode_workflow-2"
PROJECT_ID = "g-p-11111111111111111111111111111111-promptbranch-test"


def _accepted_source_tree(tmp_path: Path) -> Path:
    root = tmp_path / "accepted-source"
    root.mkdir()
    (root / "VERSION").write_text(SOURCE_VERSION + "\n", encoding="utf-8")
    for rel in [
        Path(".promptbranch/ai-registry.json"),
        Path(".promptbranch/skills/promptbranch-learning"),
        Path(".promptbranch/skills/promptbranch-operator"),
        Path(".promptbranch/skills/promptbranch-tool-authoring"),
        Path(".promptbranch/skills/repo-inspection/SKILL.md"),
        Path(".promptbranch/skills/promptbranch-final-mvp/SKILL.md"),
        Path(".promptbranch/skills/application-architecture-proof/SKILL.md"),
        Path("promptbranch_protocol/schemas/tool.authoring.schema.json"),
    ]:
        source = REPO / rel
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, dest)
        else:
            shutil.copy2(source, dest)
    return root


def _accepted_zip(tmp_path: Path) -> Path:
    source = _accepted_source_tree(tmp_path)
    artifact = tmp_path / f"{REPO_ID}_{SOURCE_VERSION}.zip"
    with zipfile.ZipFile(artifact, "w", compression=zipfile.ZIP_STORED) as archive:
        for path in sorted(item for item in source.rglob("*") if item.is_file()):
            archive.write(path, path.relative_to(source).as_posix())
    return artifact


def _configure_authority(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path]:
    state_home = tmp_path / "state"
    config_home = tmp_path / "config"
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(state_home))
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", str(config_home))
    source_binding = tmp_path / "pb-source-binding"
    source_binding.mkdir()
    write_repo_identity(
        source_binding,
        project_id=PROJECT_ID,
        project_home_url="https://chatgpt.com/g/g-p-11111111111111111111111111111111/project",
        repo_id=REPO_ID,
    )
    artifact = _accepted_zip(tmp_path)
    with zipfile.ZipFile(artifact) as archive:
        file_count = len(archive.infolist())
    registry = ArtifactRegistry(project_registry_dir(PROJECT_ID))
    registry.initialize()
    registry.add(
        ArtifactRecord(
            path=str(artifact),
            filename=artifact.name,
            kind="adopted_release",
            version=SOURCE_VERSION,
            repo_path=None,
            sha256=sha256_file(artifact),
            size_bytes=artifact.stat().st_size,
            file_count=file_count,
            created_at=utc_now(),
            repo_id=REPO_ID,
        )
    )
    return source_binding, artifact


def _git_repo(tmp_path: Path) -> Path:
    target = tmp_path / "target"
    target.mkdir()
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    subprocess.run(["git", "-C", str(target), "config", "user.name", "Promptbranch Test"], check=True)
    subprocess.run(["git", "-C", str(target), "config", "user.email", "pb@example.invalid"], check=True)
    return target


def test_skill_sync_installs_from_authoritative_current_not_source_worktree(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source_binding, artifact = _configure_authority(monkeypatch, tmp_path)
    target = _git_repo(tmp_path)
    # Deliberate source-worktree drift. The source binding contains no skill tree;
    # authoritative adopted/current ZIP must remain the only content source.
    (source_binding / "UNRELEASED.txt").write_text("must never be synced\n", encoding="utf-8")

    payload = sync_skills(target_repo=target, source_repo=source_binding)

    assert payload["ok"] is True
    assert payload["status"] == "skills_synced"
    assert payload["authority"]["version"] == SOURCE_VERSION
    assert payload["authority"]["artifact"] != str(source_binding)
    assert Path(payload["authority"]["artifact"]).is_file()
    assert payload["authority"]["artifact_sha256"] == sha256_file(Path(payload["authority"]["artifact"]))
    for skill in ("promptbranch-learning", "promptbranch-operator", "promptbranch-tool-authoring"):
        assert (target / ".promptbranch" / "skills" / skill / "SKILL.md").is_file()
        assert payload["validations"][skill]["ok"] is True
    assert not (target / ".promptbranch" / "skills" / "UNRELEASED.txt").exists()
    provenance = json.loads((target / ".promptbranch" / "promptbranch-skills.json").read_text(encoding="utf-8"))
    assert provenance["source"]["version"] == SOURCE_VERSION
    assert provenance["source"]["artifact_sha256"] == sha256_file(Path(payload["authority"]["artifact"]))
    assert payload["commit_performed"] is False


def test_skill_sync_is_idempotent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source_binding, _ = _configure_authority(monkeypatch, tmp_path)
    target = _git_repo(tmp_path)
    first = sync_skills(target_repo=target, source_repo=source_binding)
    second = sync_skills(target_repo=target, source_repo=source_binding)
    assert first["ok"] is True
    assert second["ok"] is True
    assert second["status"] == "already_synced"
    assert second["mutation_performed"] is False


def test_skill_sync_detects_local_managed_skill_drift(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source_binding, _ = _configure_authority(monkeypatch, tmp_path)
    target = _git_repo(tmp_path)
    assert sync_skills(target_repo=target, source_repo=source_binding)["ok"] is True
    skill = target / ".promptbranch" / "skills" / "promptbranch-learning" / "SKILL.md"
    skill.write_text(skill.read_text(encoding="utf-8") + "\nlocal edit\n", encoding="utf-8")

    blocked = sync_skills(target_repo=target, source_repo=source_binding)
    assert blocked["ok"] is False
    assert blocked["status"] == "preflight_failed"
    assert any("managed_skill_modified:promptbranch-learning" in item for item in blocked["errors"])

    forced = sync_skills(target_repo=target, source_repo=source_binding, force=True)
    assert forced["ok"] is True
    assert "local edit" not in skill.read_text(encoding="utf-8")


def test_skill_sync_dry_run_does_not_mutate(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source_binding, _ = _configure_authority(monkeypatch, tmp_path)
    target = _git_repo(tmp_path)
    payload = sync_skills(target_repo=target, source_repo=source_binding, dry_run=True)
    assert payload["ok"] is True
    assert payload["status"] == "dry_run"
    assert payload["plan"]["would_change"] is True
    assert payload["mutation_performed"] is False
    assert not (target / ".promptbranch").exists()


def test_skill_sync_requires_authoritative_current(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    source = tmp_path / "source"
    source.mkdir()
    write_repo_identity(source, project_id=PROJECT_ID, project_home_url=None, repo_id=REPO_ID)
    target = _git_repo(tmp_path)
    payload = sync_skills(target_repo=target, source_repo=source)
    assert payload["ok"] is False
    assert payload["status"] == "preflight_failed"
    assert any("source_project_registry_unavailable" in item for item in payload["errors"])


def test_skill_sync_rolls_back_target_and_provenance_on_post_install_validation_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import promptbranch_skill_sync as module

    source_binding, _ = _configure_authority(monkeypatch, tmp_path)
    target = _git_repo(tmp_path)
    first = sync_skills(target_repo=target, source_repo=source_binding)
    assert first["ok"] is True
    skill = target / ".promptbranch" / "skills" / "promptbranch-learning" / "SKILL.md"
    skill.write_text(skill.read_text(encoding="utf-8") + "\noperator-owned local drift\n", encoding="utf-8")
    provenance_path = target / ".promptbranch" / "promptbranch-skills.json"
    provenance_before = provenance_path.read_bytes()
    skill_before = skill.read_bytes()

    real_validate = module.skill_validate
    def fail_operator(name: str, *, repo_path):
        if name == "promptbranch-operator":
            return {"ok": False, "errors": ["synthetic_post_install_failure"]}
        return real_validate(name, repo_path=repo_path)
    monkeypatch.setattr(module, "skill_validate", fail_operator)

    payload = sync_skills(target_repo=target, source_repo=source_binding, force=True)
    assert payload["ok"] is False
    assert payload["status"] == "transaction_rolled_back"
    assert payload["rollback_performed"] is True
    assert skill.read_bytes() == skill_before
    assert provenance_path.read_bytes() == provenance_before


def test_skill_sync_module_is_declared_in_installed_package_surface() -> None:
    import tomllib

    payload = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    modules = payload["tool"]["setuptools"]["py-modules"]
    assert "promptbranch_skill_sync" in modules
