from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from promptbranch_artifacts import ArtifactRegistry, sha256_file
from promptbranch_learning import export_learning_bundle, verify_learning_bundle
from promptbranch_mcp import skill_validate
from promptbranch_project import load_repo_identity, project_registry_dir
from promptbranch_tool_authoring import export_tool_authoring_bundle, verify_tool_authoring_bundle

SYNC_SCHEMA = "promptbranch.external_repo.skills"
SYNC_SCHEMA_VERSION = "1.0"
SUPPORTED_SKILLS = (
    "promptbranch-learning",
    "promptbranch-operator",
    "promptbranch-tool-authoring",
)


class SkillSyncError(RuntimeError):
    pass


def _safe_extract_root(bundle: Path, *, skill: str, destination: Path) -> None:
    root = f"{skill}/"
    with zipfile.ZipFile(bundle, "r") as archive:
        names = archive.namelist()
        if not names or not all(name.startswith(root) for name in names):
            raise SkillSyncError(f"bundle root does not match skill {skill}")
        for info in archive.infolist():
            path = PurePosixPath(info.filename)
            if path.is_absolute() or ".." in path.parts:
                raise SkillSyncError(f"unsafe bundle path: {info.filename}")
        archive.extractall(destination)


def _git_snapshot(target: Path) -> dict[str, Any]:
    if not (target / ".git").exists():
        return {"is_git_repo": False, "status_short": [], "diff_stat": ""}
    status = subprocess.run(
        ["git", "status", "--short", "--", ".promptbranch"],
        cwd=target,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    diff = subprocess.run(
        ["git", "diff", "--stat", "--", ".promptbranch"],
        cwd=target,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "is_git_repo": status.returncode == 0,
        "status_short": [line for line in status.stdout.splitlines() if line.strip()] if status.returncode == 0 else [],
        "diff_stat": diff.stdout.strip() if diff.returncode == 0 else "",
    }


def _resolve_authoritative_source(source_repo: Path) -> tuple[dict[str, Any], Path]:
    identity = load_repo_identity(source_repo)
    if identity is None:
        raise SkillSyncError(f"source repository has no .promptbranch-repo.json: {source_repo}")
    registry = ArtifactRegistry(project_registry_dir(identity.project_id))
    state = registry.inspect()
    if state.get("ok") is not True:
        raise SkillSyncError(f"authoritative project artifact registry unavailable: {state.get('status')}: {state.get('error')}")
    record = registry.current(repo_id=identity.repo_id)
    if not isinstance(record, dict):
        raise SkillSyncError(f"no adopted/current artifact exists for source repo {identity.repo_id}")
    if str(record.get("kind") or "") != "adopted_release":
        raise SkillSyncError("source current artifact is not kind=adopted_release")
    version = str(record.get("version") or "").strip()
    expected_sha = str(record.get("sha256") or "").strip().lower()
    filename = str(record.get("filename") or "").strip()
    path = Path(str(record.get("path") or "")).expanduser()
    if not version or len(expected_sha) != 64 or not filename:
        raise SkillSyncError("source adopted/current record lacks exact version/SHA/filename authority")
    if not path.is_file():
        canonical = registry.object_path(expected_sha, filename)
        if canonical.is_file():
            path = canonical
        else:
            raise SkillSyncError(f"authoritative source artifact bytes unavailable: {path}")
    actual_sha = sha256_file(path)
    if actual_sha != expected_sha:
        raise SkillSyncError(f"authoritative source artifact SHA mismatch: expected={expected_sha} actual={actual_sha}")
    try:
        with zipfile.ZipFile(path, "r") as archive:
            archive.testzip()
            embedded_version = archive.read("VERSION").decode("utf-8").strip()
    except (OSError, KeyError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
        raise SkillSyncError(f"authoritative source artifact is not a valid Promptbranch ZIP: {exc}") from exc
    if embedded_version != version:
        raise SkillSyncError(f"authoritative source artifact VERSION mismatch: record={version} embedded={embedded_version}")
    return {
        "project_id": identity.project_id,
        "repo_id": identity.repo_id,
        "version": version,
        "filename": filename,
        "sha256": expected_sha,
        "path": str(path.resolve()),
        "registry_file": str(registry.path),
    }, path.resolve()


def _export_and_verify(skill: str, accepted_root: Path, output: Path) -> dict[str, Any]:
    if skill == "promptbranch-tool-authoring":
        exported = export_tool_authoring_bundle(accepted_root, output, force=True)
        verified = verify_tool_authoring_bundle(output)
    else:
        exported = export_learning_bundle(skill, accepted_root, output, force=True)
        verified = verify_learning_bundle(output)
    if exported.get("ok") is not True or verified.get("ok") is not True:
        raise SkillSyncError(f"portable bundle export/verification failed for {skill}: {verified.get('errors') or exported.get('errors')}")
    return {
        "skill": skill,
        "bundle_path": str(output),
        "bundle_sha256": sha256_file(output),
        "bundle_size_bytes": output.stat().st_size,
        "bundle_entry_count": int(verified.get("entry_count") or 0),
        "verification_status": verified.get("status"),
    }


def sync_promptbranch_skills(
    target_repo: str | Path,
    *,
    source_repo: str | Path = ".",
    skills: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    target = Path(target_repo).expanduser().resolve()
    source = Path(source_repo).expanduser().resolve()
    requested = list(skills or SUPPORTED_SKILLS)
    if not target.is_dir():
        return {"ok": False, "action": "skill_sync", "status": "target_repo_missing", "target_repo": str(target), "errors": ["target repository directory does not exist"], "mutation_performed": False}
    if not source.is_dir():
        return {"ok": False, "action": "skill_sync", "status": "source_repo_missing", "source_repo": str(source), "errors": ["source repository directory does not exist"], "mutation_performed": False}
    unknown = [name for name in requested if name not in SUPPORTED_SKILLS]
    if unknown:
        return {"ok": False, "action": "skill_sync", "status": "unsupported_skill", "skills": requested, "errors": [f"unsupported skill(s): {', '.join(unknown)}"], "mutation_performed": False}
    if len(set(requested)) != len(requested):
        return {"ok": False, "action": "skill_sync", "status": "duplicate_skill", "skills": requested, "errors": ["each skill may be requested only once"], "mutation_performed": False}

    before_git = _git_snapshot(target)
    try:
        authority, artifact_path = _resolve_authoritative_source(source)
    except (SkillSyncError, ValueError) as exc:
        return {"ok": False, "action": "skill_sync", "status": "source_authority_unavailable", "source_repo": str(source), "target_repo": str(target), "errors": [str(exc)], "mutation_performed": False}

    pb_root = target / ".promptbranch"
    skills_root = pb_root / "skills"
    provenance_path = pb_root / "promptbranch-skills.json"
    pb_root.mkdir(parents=True, exist_ok=True)
    skills_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="promptbranch-skill-sync-") as tmp_name:
        tmp = Path(tmp_name)
        accepted_root = tmp / "accepted"
        accepted_root.mkdir()
        try:
            with zipfile.ZipFile(artifact_path, "r") as archive:
                for info in archive.infolist():
                    path = PurePosixPath(info.filename)
                    if path.is_absolute() or ".." in path.parts:
                        raise SkillSyncError(f"unsafe source artifact path: {info.filename}")
                archive.extractall(accepted_root)
        except (OSError, zipfile.BadZipFile, SkillSyncError) as exc:
            return {"ok": False, "action": "skill_sync", "status": "source_artifact_extract_failed", "source_authority": authority, "errors": [str(exc)], "mutation_performed": False}

        stage_root = pb_root / f".skill-sync-stage-{os.getpid()}"
        backup_root = pb_root / f".skill-sync-backup-{os.getpid()}"
        shutil.rmtree(stage_root, ignore_errors=True)
        shutil.rmtree(backup_root, ignore_errors=True)
        stage_root.mkdir(parents=True)
        bundle_records: list[dict[str, Any]] = []
        try:
            for skill in requested:
                bundle = tmp / f"{skill}_{authority['version']}.zip"
                record = _export_and_verify(skill, accepted_root, bundle)
                extract_dir = tmp / f"extract-{skill}"
                extract_dir.mkdir()
                _safe_extract_root(bundle, skill=skill, destination=extract_dir)
                staged = stage_root / skill
                shutil.copytree(extract_dir / skill, staged)
                validation = skill_validate(str(staged / "SKILL.md"), repo_path=target)
                if validation.get("ok") is not True:
                    raise SkillSyncError(f"staged skill validation failed for {skill}: {validation.get('errors')}")
                record["installed_path"] = str((skills_root / skill).relative_to(target))
                bundle_records.append(record)

            provenance = {
                "schema": SYNC_SCHEMA,
                "schema_version": SYNC_SCHEMA_VERSION,
                "source": {
                    "project_id": authority["project_id"],
                    "repo_id": authority["repo_id"],
                    "promptbranch_version": authority["version"],
                    "artifact_filename": authority["filename"],
                    "artifact_sha256": authority["sha256"],
                },
                "target_repo": str(target),
                "skills": {
                    item["skill"]: {
                        "bundle_sha256": item["bundle_sha256"],
                        "bundle_size_bytes": item["bundle_size_bytes"],
                        "bundle_entry_count": item["bundle_entry_count"],
                        "installed_path": item["installed_path"],
                    }
                    for item in bundle_records
                },
            }
            provenance_bytes = (json.dumps(provenance, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")

            backup_root.mkdir(parents=True)
            replaced: list[str] = []
            newly_created: list[str] = []
            try:
                for skill in requested:
                    dst = skills_root / skill
                    backup = backup_root / skill
                    if dst.exists():
                        os.replace(dst, backup)
                        replaced.append(skill)
                    else:
                        newly_created.append(skill)
                    os.replace(stage_root / skill, dst)
                provenance_backup = backup_root / "promptbranch-skills.json"
                if provenance_path.exists():
                    os.replace(provenance_path, provenance_backup)
                temp_provenance = pb_root / f".promptbranch-skills.{os.getpid()}.tmp"
                temp_provenance.write_bytes(provenance_bytes)
                os.replace(temp_provenance, provenance_path)

                validations: dict[str, Any] = {}
                for skill in requested:
                    validations[skill] = skill_validate(skill, repo_path=target)
                    if validations[skill].get("ok") is not True:
                        raise SkillSyncError(f"target validation failed for {skill}: {validations[skill].get('errors')}")
            except Exception:
                for skill in requested:
                    dst = skills_root / skill
                    if dst.exists():
                        shutil.rmtree(dst)
                    backup = backup_root / skill
                    if backup.exists():
                        os.replace(backup, dst)
                if provenance_path.exists():
                    provenance_path.unlink()
                provenance_backup = backup_root / "promptbranch-skills.json"
                if provenance_backup.exists():
                    os.replace(provenance_backup, provenance_path)
                raise
        except (OSError, SkillSyncError, zipfile.BadZipFile) as exc:
            shutil.rmtree(stage_root, ignore_errors=True)
            shutil.rmtree(backup_root, ignore_errors=True)
            return {
                "ok": False,
                "action": "skill_sync",
                "status": "sync_failed",
                "source_authority": authority,
                "source_repo": str(source),
                "target_repo": str(target),
                "skills": requested,
                "errors": [str(exc)],
                "mutation_performed": False,
            }
        finally:
            shutil.rmtree(stage_root, ignore_errors=True)
            shutil.rmtree(backup_root, ignore_errors=True)

    after_git = _git_snapshot(target)
    return {
        "ok": True,
        "action": "skill_sync",
        "status": "skills_synced",
        "source_repo": str(source),
        "target_repo": str(target),
        "source_authority": authority,
        "skills": bundle_records,
        "provenance_path": str(provenance_path),
        "provenance_sha256": hashlib.sha256(provenance_path.read_bytes()).hexdigest(),
        "target_validation": {name: skill_validate(name, repo_path=target) for name in requested},
        "git_before": before_git,
        "git_after": after_git,
        "mutation_performed": True,
        "git_commit_performed": False,
        "git_push_performed": False,
    }
