from __future__ import annotations

import argparse
import json
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest

from promptbranch_artifacts import (
    ArtifactIdentityConflictError,
    ArtifactRecord,
    ArtifactRegistry,
    create_repo_snapshot,
    verify_zip_artifact,
)
from promptbranch_cli import _artifact_current_payload, _repo_doctor_payload, _resolve_adopt_local_zip
from promptbranch_project import join_local_repo, load_repo_identity, project_registry_dir, write_repo_identity
from promptbranch_state import ConversationStateStore


def _write_zip(path: Path, *, version: str, marker: str) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("VERSION", version + "\n")
        archive.writestr("payload.txt", marker + "\n")
    result = verify_zip_artifact(path)
    assert result["ok"] is True
    return result


def _record(path: Path, *, repo_id: str, version: str, kind: str, marker: str, created_at: str = "2026-08-11T00:00:00Z") -> ArtifactRecord:
    verification = _write_zip(path, version=version, marker=marker)
    return ArtifactRecord(
        path=str(path),
        filename=path.name,
        kind=kind,
        version=version,
        repo_path=None,
        repo_id=repo_id,
        sha256=str(verification["sha256"]),
        size_bytes=int(verification["size_bytes"]),
        file_count=int(verification["entry_count"]),
        created_at=created_at,
        source_ref=path.name,
    )


def _project(monkeypatch, tmp_path: Path, *, repo_id: str = "vault", version: str = "v1.0.0") -> tuple[Path, ArtifactRegistry, str]:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", str(tmp_path / "config"))
    project_id = "g-p-0123456789abcdef0123456789abcdef-demo"
    project_url = f"https://chatgpt.com/g/{project_id}/project"
    repo = tmp_path / repo_id
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "VERSION").write_text(version + "\n", encoding="utf-8")
    (repo / "README.md").write_text("demo\n", encoding="utf-8")
    write_repo_identity(
        repo,
        project_id=project_id,
        project_home_url=project_url,
        repo_id=repo_id,
        artifact_pattern=f"{repo_id}_<version>.zip",
        role="primary",
    )
    identity = load_repo_identity(repo)
    assert identity is not None
    join_local_repo(identity)
    registry = ArtifactRegistry(project_registry_dir(project_id))
    registry.initialize()
    monkeypatch.chdir(repo)
    return repo, registry, project_url


def test_artifact_authority_one_sha_per_repo_version_rejects_release_to_adopted_conflict(tmp_path: Path) -> None:
    registry = ArtifactRegistry(tmp_path / "profile")
    registry.initialize()
    release = _record(tmp_path / "a" / "vault_v1.0.0.zip", repo_id="vault", version="v1.0.0", kind="release", marker="A")
    adopted = _record(tmp_path / "b" / "vault_v1.0.0.zip", repo_id="vault", version="v1.0.0", kind="adopted_release", marker="B")

    stored = registry.add(release)
    before = json.loads(registry.path.read_text(encoding="utf-8"))
    with pytest.raises(ArtifactIdentityConflictError) as error:
        registry.add(adopted)
    after = json.loads(registry.path.read_text(encoding="utf-8"))

    assert error.value.repo_id == "vault"
    assert error.value.version == "v1.0.0"
    assert before == after
    assert len(after["artifacts"]) == 1
    assert after["artifacts"][0]["sha256"] == stored["sha256"]


def test_artifact_authority_same_object_registration_is_idempotent_and_adoption_is_one_record(tmp_path: Path) -> None:
    registry = ArtifactRegistry(tmp_path / "profile")
    registry.initialize()
    release = _record(tmp_path / "input" / "vault_v1.0.0.zip", repo_id="vault", version="v1.0.0", kind="release", marker="same")

    first = registry.add(release)
    second = registry.add(release)
    adopted = registry.add(replace(release, kind="adopted_release", created_at="2026-08-11T00:01:00Z"))

    records = [item for item in registry.list() if item.get("repo_id") == "vault" and item.get("version") == "v1.0.0"]
    assert first["sha256"] == second["sha256"] == adopted["sha256"]
    assert len(records) == 1
    assert records[0]["kind"] == "adopted_release"
    assert registry.current("vault") == records[0]
    assert Path(records[0]["path"]).is_file()
    assert Path(records[0]["path"]).resolve().is_relative_to(registry.object_dir.resolve())


def test_artifact_authority_missing_explicit_local_path_never_falls_back_to_same_named_zip(monkeypatch, tmp_path: Path) -> None:
    registry = ArtifactRegistry(tmp_path / "profile")
    registry.initialize()
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    same_name = cwd / "vault_v1.0.0.zip"
    _write_zip(same_name, version="v1.0.0", marker="cwd")
    monkeypatch.chdir(cwd)

    resolved = _resolve_adopt_local_zip(
        "vault_v1.0.0.zip",
        local_path=str(tmp_path / "missing" / "vault_v1.0.0.zip"),
        registry=registry,
    )

    assert resolved is None


def test_artifact_authority_registered_release_resolution_uses_pb_object_not_filename_search(monkeypatch, tmp_path: Path) -> None:
    registry = ArtifactRegistry(tmp_path / "profile")
    registry.initialize()
    release = _record(tmp_path / "input" / "vault_v1.0.0.zip", repo_id="vault", version="v1.0.0", kind="release", marker="authority")
    stored = registry.add(release)
    cwd = tmp_path / "empty-cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    resolved = _resolve_adopt_local_zip("vault_v1.0.0.zip", local_path=None, registry=registry)

    assert resolved == Path(stored["path"]).resolve()
    assert resolved.is_relative_to(registry.object_dir.resolve())


def test_artifact_authority_repo_doctor_detects_competing_release_identity(monkeypatch, tmp_path: Path) -> None:
    repo, registry, project_url = _project(monkeypatch, tmp_path)
    a = _record(tmp_path / "a" / "vault_v1.0.0.zip", repo_id="vault", version="v1.0.0", kind="adopted_release", marker="A")
    b = _record(tmp_path / "b" / "vault_v1.0.0.zip", repo_id="vault", version="v1.0.0", kind="release", marker="B")
    # Seed the observed pre-fix state directly; canonical add() correctly refuses it.
    registry.path.write_text(json.dumps({"schema_version": 1, "artifacts": [a.to_dict(), b.to_dict()]}, indent=2) + "\n", encoding="utf-8")
    ConversationStateStore(str(registry.profile_dir)).remember_artifact(
        project_url=project_url,
        repo_id="vault",
        artifact_ref=a.filename,
        artifact_version=a.version,
        source_ref=a.filename,
        source_version=a.version,
    )

    payload = _repo_doctor_payload(argparse.Namespace())
    checks = {item["id"]: item for item in payload["checks"]}

    assert payload["ok"] is False
    assert checks["repo_versions_have_single_sha"]["status"] == "failed"
    assert checks["registry_artifact_identity_unique"]["status"] == "failed"


def test_artifact_authority_clean_release_adopt_current_doctor_projection_and_external_version_domain(monkeypatch, tmp_path: Path) -> None:
    repo, registry, project_url = _project(monkeypatch, tmp_path, repo_id="vault", version="v9.9.9")
    release, _ = create_repo_snapshot(repo, output_dir=tmp_path / "exports", kind="release")
    released = registry.add(release)
    assert registry.current("vault") is None
    adopted = registry.add(ArtifactRecord(
        **{**release.__dict__, "path": released["path"], "kind": "adopted_release", "created_at": "2026-08-11T00:02:00Z"}
    ))
    ConversationStateStore(str(registry.profile_dir)).remember_artifact(
        project_url=project_url,
        repo_id="vault",
        artifact_ref=adopted["filename"],
        artifact_version=adopted["version"],
        source_ref=adopted["filename"],
        source_version=adopted["version"],
    )

    current = _artifact_current_payload(
        None,
        registry,
        repo_id="vault",
        all_repos=False,
        state_store=ConversationStateStore(str(registry.profile_dir)),
    )
    doctor = _repo_doctor_payload(argparse.Namespace())
    doctor_checks = {item["id"]: item for item in doctor["checks"]}

    assert current["ok"] is True
    repo_current = current["repos"]["vault"]
    assert repo_current["registry_current"]["sha256"] == released["sha256"]
    assert repo_current["consistency"]["state_projection_matches_registry"] is True
    assert repo_current["consistency"]["current_artifact_object_exists"] is True
    assert repo_current["consistency"]["current_artifact_sha_exact"] is True
    assert repo_current["baseline_roles"]["code_version_relation"] == "external_repo_baseline"
    assert repo_current["baseline_roles"]["code_version_match_applicable"] is False
    assert doctor["ok"] is True
    assert doctor_checks["repo_versions_have_single_sha"]["status"] == "passed"
    assert doctor_checks["registry_artifact_identity_unique"]["status"] == "passed"
    assert doctor_checks["current_artifact_object_exists"]["status"] == "passed"
    assert doctor_checks["current_artifact_sha_exact"]["status"] == "passed"
    assert doctor_checks["current_artifact_under_pb_object_authority"]["status"] == "passed"
    assert doctor_checks["state_projection_matches_registry"]["status"] == "passed"
