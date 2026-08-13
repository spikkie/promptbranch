from __future__ import annotations

import json
import os
import zipfile
from pathlib import Path

from promptbranch_artifacts import ArtifactRecord, ArtifactRegistry, sha256_file, utc_now
from promptbranch_project import project_registry_dir
from promptbranch_skill_sync import SUPPORTED_SKILLS, sync_promptbranch_skills


def _source_artifact(root: Path, tmp_path: Path, *, repo_id: str, version: str) -> Path:
    artifact = tmp_path / f"{repo_id}_{version}.zip"
    entries = [
        Path("VERSION"),
        Path(".promptbranch/ai-registry.json"),
        Path("promptbranch_protocol/schemas/tool.authoring.schema.json"),
        Path(".promptbranch/skills/repo-inspection/SKILL.md"),
        Path(".promptbranch/skills/promptbranch-final-mvp/SKILL.md"),
        Path(".promptbranch/skills/application-architecture-proof/SKILL.md"),
    ]
    for base in (
        root / ".promptbranch/skills/promptbranch-learning",
        root / ".promptbranch/skills/promptbranch-operator",
        root / ".promptbranch/skills/promptbranch-tool-authoring",
    ):
        entries.extend(path.relative_to(root) for path in base.rglob("*") if path.is_file())
    with zipfile.ZipFile(artifact, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for rel in sorted(set(entries), key=lambda p: p.as_posix()):
            archive.write(root / rel, rel.as_posix())
    return artifact


def _prepare_authority(tmp_path: Path, monkeypatch, *, artifact: Path, repo_id: str, version: str) -> Path:
    project_id = "g-p-00000000000000000000000000000000-skill-sync"
    source_repo = tmp_path / "source-repo"
    source_repo.mkdir()
    (source_repo / ".promptbranch-repo.json").write_text(json.dumps({
        "schema_version": 1,
        "project_id": project_id,
        "project_home_url": "https://chatgpt.com/g/g-p-00000000000000000000000000000000-skill-sync/project",
        "repo_id": repo_id,
        "artifact_pattern": f"{repo_id}_<version>.zip",
        "role": "member",
    }) + "\n", encoding="utf-8")
    state_home = tmp_path / "project-state"
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(state_home))
    registry = ArtifactRegistry(project_registry_dir(project_id))
    registry.initialize()
    with zipfile.ZipFile(artifact, "r") as archive:
        file_count = len(archive.namelist())
    registry.add(ArtifactRecord(
        path=str(artifact),
        filename=artifact.name,
        kind="adopted_release",
        version=version,
        repo_path=None,
        sha256=sha256_file(artifact),
        size_bytes=artifact.stat().st_size,
        file_count=file_count,
        created_at=utc_now(),
        repo_id=repo_id,
        project_url="https://chatgpt.com/g/g-p-00000000000000000000000000000000-skill-sync/project",
    ))
    return source_repo


def test_skill_sync_installs_verified_current_skills_and_provenance(tmp_path: Path, monkeypatch) -> None:
    root = Path(__file__).resolve().parents[1]
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    repo_id = "promptbranch-source"
    artifact = _source_artifact(root, tmp_path, repo_id=repo_id, version=version)
    source_repo = _prepare_authority(tmp_path, monkeypatch, artifact=artifact, repo_id=repo_id, version=version)
    target = tmp_path / "external-app"
    target.mkdir()

    payload = sync_promptbranch_skills(target, source_repo=source_repo)

    assert payload["ok"] is True, payload
    assert payload["status"] == "skills_synced"
    assert payload["source_authority"]["version"] == version
    assert payload["source_authority"]["sha256"] == sha256_file(artifact)
    assert [item["skill"] for item in payload["skills"]] == list(SUPPORTED_SKILLS)
    for skill in SUPPORTED_SKILLS:
        assert (target / ".promptbranch/skills" / skill / "SKILL.md").is_file()
        assert payload["target_validation"][skill]["ok"] is True
    provenance = json.loads((target / ".promptbranch/promptbranch-skills.json").read_text(encoding="utf-8"))
    assert provenance["schema"] == "promptbranch.external_repo.skills"
    assert provenance["source"]["promptbranch_version"] == version
    assert provenance["source"]["artifact_sha256"] == sha256_file(artifact)
    assert set(provenance["skills"]) == set(SUPPORTED_SKILLS)
    assert payload["git_commit_performed"] is False
    assert payload["git_push_performed"] is False


def test_skill_sync_is_idempotent_for_same_authoritative_source(tmp_path: Path, monkeypatch) -> None:
    root = Path(__file__).resolve().parents[1]
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    repo_id = "promptbranch-source"
    artifact = _source_artifact(root, tmp_path, repo_id=repo_id, version=version)
    source_repo = _prepare_authority(tmp_path, monkeypatch, artifact=artifact, repo_id=repo_id, version=version)
    target = tmp_path / "external-app"; target.mkdir()
    first = sync_promptbranch_skills(target, source_repo=source_repo)
    before = (target / ".promptbranch/promptbranch-skills.json").read_bytes()
    second = sync_promptbranch_skills(target, source_repo=source_repo)
    after = (target / ".promptbranch/promptbranch-skills.json").read_bytes()
    assert first["ok"] is True and second["ok"] is True
    assert before == after
    assert first["provenance_sha256"] == second["provenance_sha256"]


def test_skill_sync_fails_closed_when_authoritative_bytes_are_tampered(tmp_path: Path, monkeypatch) -> None:
    root = Path(__file__).resolve().parents[1]
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    repo_id = "promptbranch-source"
    artifact = _source_artifact(root, tmp_path, repo_id=repo_id, version=version)
    source_repo = _prepare_authority(tmp_path, monkeypatch, artifact=artifact, repo_id=repo_id, version=version)
    # The registry object is immutable and canonical. Corrupt it after registration.
    identity = json.loads((source_repo / ".promptbranch-repo.json").read_text())
    registry = ArtifactRegistry(project_registry_dir(identity["project_id"]))
    record = registry.current(repo_id=repo_id)
    assert record is not None
    Path(record["path"]).write_bytes(b"corrupt")
    target = tmp_path / "external-app"; target.mkdir()
    payload = sync_promptbranch_skills(target, source_repo=source_repo)
    assert payload["ok"] is False
    assert payload["status"] == "source_authority_unavailable"
    assert payload["mutation_performed"] is False
    assert not (target / ".promptbranch/skills").exists()


def test_skill_sync_module_is_declared_installable():
    import tomllib
    from pathlib import Path
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert "promptbranch_skill_sync" in data["tool"]["setuptools"]["py-modules"]
