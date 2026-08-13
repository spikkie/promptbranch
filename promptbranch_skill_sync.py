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

from promptbranch_artifacts import (
    ArtifactRegistry,
    canonical_version_tag,
    parse_canonical_artifact_filename,
    sha256_file,
    verify_zip_artifact,
)
from promptbranch_learning import (
    LEARNING_SKILL,
    OPERATOR_SKILL,
    export_learning_bundle,
    verify_learning_bundle,
)
from promptbranch_mcp import skill_validate, validate_skill_document
from promptbranch_project import load_repo_identity, project_registry_dir
from promptbranch_tool_authoring import (
    SKILL_NAME as TOOL_AUTHORING_SKILL,
    export_tool_authoring_bundle,
    verify_tool_authoring_bundle,
)

SYNC_SCHEMA = "promptbranch.external_repo.skills"
SYNC_SCHEMA_VERSION = "1.0"
SUPPORTED_SKILLS = (LEARNING_SKILL, OPERATOR_SKILL, TOOL_AUTHORING_SKILL)
PROVENANCE_REL = Path(".promptbranch/promptbranch-skills.json")
SKILLS_REL = Path(".promptbranch/skills")


class SkillSyncError(ValueError):
    pass


def _canonical_json(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _tree_digest(root: Path) -> str:
    if not root.is_dir():
        raise SkillSyncError(f"skill_tree_missing:{root}")
    digest = hashlib.sha256()
    files = sorted(path for path in root.rglob("*") if path.is_file())
    for path in files:
        rel = path.relative_to(root).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(rel).to_bytes(8, "big"))
        digest.update(rel)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _git_root(target: Path) -> tuple[Path | None, str | None]:
    proc = subprocess.run(
        ["git", "-C", str(target), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return None, (proc.stderr or proc.stdout or "git rev-parse failed").strip()
    try:
        return Path(proc.stdout.strip()).resolve(), None
    except OSError as exc:
        return None, str(exc)


def _git_status(target: Path) -> dict[str, Any]:
    paths = [SKILLS_REL.as_posix(), PROVENANCE_REL.as_posix()]
    proc = subprocess.run(
        ["git", "-C", str(target), "status", "--short", "--", *paths],
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "lines": [line for line in proc.stdout.splitlines() if line.strip()],
        "stderr": proc.stderr.strip() or None,
    }


def _safe_extract(archive_path: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive_path, "r") as archive:
        for info in archive.infolist():
            pure = PurePosixPath(info.filename)
            if pure.is_absolute() or ".." in pure.parts:
                raise SkillSyncError(f"unsafe_zip_entry:{info.filename}")
            if info.is_dir():
                continue
            output = (destination / Path(*pure.parts)).resolve()
            try:
                output.relative_to(destination.resolve())
            except ValueError as exc:
                raise SkillSyncError(f"unsafe_zip_entry:{info.filename}") from exc
            output.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info, "r") as source, output.open("wb") as sink:
                shutil.copyfileobj(source, sink)


def _read_embedded_version(artifact: Path) -> str:
    try:
        with zipfile.ZipFile(artifact, "r") as archive:
            return archive.read("VERSION").decode("utf-8", errors="strict").strip()
    except (OSError, zipfile.BadZipFile, KeyError, UnicodeDecodeError) as exc:
        raise SkillSyncError(f"accepted_artifact_version_unavailable:{exc}") from exc


def _resolve_authoritative_source(source_repo: Path) -> dict[str, Any]:
    try:
        identity = load_repo_identity(source_repo)
    except ValueError as exc:
        raise SkillSyncError(f"source_repo_identity_invalid:{exc}") from exc
    if identity is None:
        raise SkillSyncError("source_repo_identity_missing")
    registry = ArtifactRegistry(project_registry_dir(identity.project_id))
    inspection = registry.inspect()
    if not inspection.get("ok"):
        raise SkillSyncError(f"source_project_registry_unavailable:{inspection.get('status')}")
    current = registry.current(identity.repo_id)
    if not isinstance(current, dict):
        raise SkillSyncError("source_authoritative_current_missing_or_ambiguous")
    checks = {
        "kind_adopted_release": current.get("kind") == "adopted_release",
        "repo_id_exact": current.get("repo_id") == identity.repo_id,
        "sha256_present": isinstance(current.get("sha256"), str) and len(str(current.get("sha256"))) == 64,
        "version_present": bool(canonical_version_tag(current.get("version") if isinstance(current.get("version"), str) else None)),
        "filename_canonical": parse_canonical_artifact_filename(str(current.get("filename") or "")) is not None,
    }
    if not all(checks.values()):
        failed = [name for name, ok in checks.items() if not ok]
        raise SkillSyncError("source_authoritative_current_invalid:" + ",".join(failed))
    artifact = Path(str(current.get("path") or "")).expanduser().resolve()
    if not artifact.is_file():
        raise SkillSyncError(f"source_authoritative_artifact_missing:{artifact}")
    verification = verify_zip_artifact(artifact)
    if not verification.get("ok"):
        raise SkillSyncError("source_authoritative_artifact_invalid")
    observed_sha = sha256_file(artifact)
    expected_sha = str(current.get("sha256") or "")
    if observed_sha != expected_sha:
        raise SkillSyncError(f"source_authoritative_sha_mismatch:{expected_sha}:{observed_sha}")
    embedded = canonical_version_tag(_read_embedded_version(artifact))
    record_version = canonical_version_tag(str(current.get("version") or ""))
    if not embedded or embedded != record_version:
        raise SkillSyncError(f"source_authoritative_version_mismatch:{record_version}:{embedded}")
    if artifact.name != str(current.get("filename") or ""):
        raise SkillSyncError("source_authoritative_filename_mismatch")
    return {
        "project_id": identity.project_id,
        "repo_id": identity.repo_id,
        "repo_identity_path": str(identity.path),
        "registry_file": str(registry.path),
        "version": record_version,
        "artifact": str(artifact),
        "artifact_filename": artifact.name,
        "artifact_sha256": expected_sha,
        "artifact_size_bytes": artifact.stat().st_size,
        "record": current,
        "checks": checks,
    }


def _export_bundle(skill: str, source_repo: Path, output: Path) -> dict[str, Any]:
    try:
        if skill == TOOL_AUTHORING_SKILL:
            exported = export_tool_authoring_bundle(source_repo, output, force=True)
            verified = verify_tool_authoring_bundle(output)
        elif skill in {LEARNING_SKILL, OPERATOR_SKILL}:
            exported = export_learning_bundle(skill, source_repo, output, force=True)
            verified = verify_learning_bundle(output)
        else:
            raise SkillSyncError(f"unsupported_skill:{skill}")
    except SkillSyncError:
        raise
    except Exception as exc:
        raise SkillSyncError(f"bundle_export_failed:{skill}:{type(exc).__name__}:{exc}") from exc
    if not exported.get("ok") or not verified.get("ok"):
        raise SkillSyncError(f"bundle_export_or_verify_failed:{skill}")
    if verified.get("skill") and verified.get("skill") != skill:
        raise SkillSyncError(f"bundle_skill_identity_mismatch:{skill}:{verified.get('skill')}")
    return {"export": exported, "verification": verified}


def _read_provenance(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SkillSyncError(f"provenance_invalid:{exc}") from exc
    if not isinstance(payload, dict):
        raise SkillSyncError("provenance_invalid:not_object")
    if payload.get("schema") != SYNC_SCHEMA or payload.get("schema_version") != SYNC_SCHEMA_VERSION:
        raise SkillSyncError("provenance_invalid:schema")
    skills = payload.get("skills")
    if not isinstance(skills, dict):
        raise SkillSyncError("provenance_invalid:skills")
    return payload


def _validate_existing_managed_skill(target: Path, skill: str, provenance: dict[str, Any] | None, *, force: bool) -> dict[str, Any]:
    installed = target / SKILLS_REL / skill
    if not installed.exists():
        return {"status": "absent", "managed": False, "modified": False}
    skills = provenance.get("skills") if isinstance(provenance, dict) and isinstance(provenance.get("skills"), dict) else {}
    entry = skills.get(skill) if isinstance(skills, dict) else None
    if not isinstance(entry, dict):
        if force:
            return {"status": "unmanaged_force_replace", "managed": False, "modified": True}
        raise SkillSyncError(f"unmanaged_skill_exists:{skill}")
    expected = str(entry.get("installed_tree_sha256") or "")
    if not expected:
        if force:
            return {"status": "managed_digest_missing_force_replace", "managed": True, "modified": True}
        raise SkillSyncError(f"managed_skill_digest_missing:{skill}")
    actual = _tree_digest(installed)
    modified = actual != expected
    if modified and not force:
        raise SkillSyncError(f"managed_skill_modified:{skill}:{expected}:{actual}")
    return {
        "status": "managed_modified_force_replace" if modified else "managed_intact",
        "managed": True,
        "modified": modified,
        "expected_tree_sha256": expected,
        "actual_tree_sha256": actual,
    }


def sync_skills(
    *,
    target_repo: str | Path,
    source_repo: str | Path = ".",
    skills: list[str] | tuple[str, ...] | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    source = Path(source_repo).expanduser().resolve()
    target = Path(target_repo).expanduser().resolve()
    selected = list(skills or SUPPORTED_SKILLS)
    if not selected:
        selected = list(SUPPORTED_SKILLS)
    if len(selected) != len(set(selected)):
        return {"ok": False, "action": "skill_sync", "status": "invalid_request", "errors": ["duplicate_skill"]}
    unsupported = [skill for skill in selected if skill not in SUPPORTED_SKILLS]
    if unsupported:
        return {"ok": False, "action": "skill_sync", "status": "unsupported_skill", "skills": selected, "errors": [f"unsupported_skill:{item}" for item in unsupported]}
    if not source.is_dir():
        return {"ok": False, "action": "skill_sync", "status": "source_repo_missing", "errors": [str(source)]}
    if not target.is_dir():
        return {"ok": False, "action": "skill_sync", "status": "target_repo_missing", "errors": [str(target)]}

    git_root, git_error = _git_root(target)
    if git_root is None:
        return {"ok": False, "action": "skill_sync", "status": "target_not_git_repo", "target_repo": str(target), "errors": [git_error or "git repository required"]}
    if git_root != target:
        return {"ok": False, "action": "skill_sync", "status": "target_not_git_root", "target_repo": str(target), "git_root": str(git_root), "errors": ["--target must be the Git repository root"]}

    try:
        authority = _resolve_authoritative_source(source)
        provenance_path = target / PROVENANCE_REL
        existing_provenance = _read_provenance(provenance_path)
        existing_checks = {
            skill: _validate_existing_managed_skill(target, skill, existing_provenance, force=force)
            for skill in selected
        }
    except SkillSyncError as exc:
        return {"ok": False, "action": "skill_sync", "status": "preflight_failed", "target_repo": str(target), "source_repo": str(source), "skills": selected, "errors": [str(exc)]}

    before_git = _git_status(target)
    with tempfile.TemporaryDirectory(prefix="promptbranch-skill-sync-") as temp_name:
        temp = Path(temp_name)
        accepted_extract = temp / "accepted"
        accepted_extract.mkdir(parents=True)
        try:
            _safe_extract(Path(authority["artifact"]), accepted_extract)
        except (SkillSyncError, OSError, zipfile.BadZipFile) as exc:
            return {"ok": False, "action": "skill_sync", "status": "accepted_artifact_extract_failed", "authority": authority, "errors": [str(exc)]}
        extracted_version = canonical_version_tag((accepted_extract / "VERSION").read_text(encoding="utf-8").strip())
        if extracted_version != authority["version"]:
            return {"ok": False, "action": "skill_sync", "status": "accepted_artifact_extract_version_mismatch", "authority": authority, "errors": [f"{authority['version']} != {extracted_version}"]}

        bundle_results: dict[str, Any] = {}
        staged_roots: dict[str, Path] = {}
        installed_entries: dict[str, Any] = {}
        try:
            for skill in selected:
                bundle = temp / f"{skill}_{authority['version']}.zip"
                result = _export_bundle(skill, accepted_extract, bundle)
                bundle_results[skill] = result
                extracted_bundle = temp / "bundles" / skill
                extracted_bundle.mkdir(parents=True, exist_ok=True)
                _safe_extract(bundle, extracted_bundle)
                root = extracted_bundle / skill
                if not root.is_dir():
                    raise SkillSyncError(f"bundle_root_missing:{skill}")
                skill_validation = validate_skill_document((root / "SKILL.md").read_text(encoding="utf-8"), source=str(root / "SKILL.md"))
                if not skill_validation.get("ok"):
                    raise SkillSyncError(f"staged_skill_invalid:{skill}:{';'.join(skill_validation.get('errors') or [])}")
                tree_sha = _tree_digest(root)
                staged_roots[skill] = root
                exported = result["export"]
                installed_entries[skill] = {
                    "source_version": authority["version"],
                    "bundle_sha256": str(exported.get("sha256") or ""),
                    "bundle_size_bytes": int(exported.get("size_bytes") or 0),
                    "bundle_entry_count": int(exported.get("entry_count") or 0),
                    "installed_tree_sha256": tree_sha,
                    "installed_path": (SKILLS_REL / skill).as_posix(),
                }
        except (SkillSyncError, OSError, UnicodeDecodeError) as exc:
            return {"ok": False, "action": "skill_sync", "status": "bundle_stage_failed", "authority": authority, "skills": selected, "errors": [str(exc)]}

        prior_skills = dict(existing_provenance.get("skills") or {}) if isinstance(existing_provenance, dict) else {}
        new_skills = dict(prior_skills)
        new_skills.update(installed_entries)
        new_provenance = {
            "schema": SYNC_SCHEMA,
            "schema_version": SYNC_SCHEMA_VERSION,
            "managed_by": "promptbranch.skill.sync",
            "source": {
                "project_id": authority["project_id"],
                "repo_id": authority["repo_id"],
                "version": authority["version"],
                "artifact_filename": authority["artifact_filename"],
                "artifact_sha256": authority["artifact_sha256"],
            },
            "skills": new_skills,
        }

        changes = []
        for skill in selected:
            current = target / SKILLS_REL / skill
            desired_sha = installed_entries[skill]["installed_tree_sha256"]
            current_sha = _tree_digest(current) if current.is_dir() else None
            changes.append({
                "skill": skill,
                "status": "no_change" if current_sha == desired_sha else ("install" if current_sha is None else "update"),
                "current_tree_sha256": current_sha,
                "desired_tree_sha256": desired_sha,
            })
        provenance_bytes = _canonical_json(new_provenance)
        old_provenance_bytes = provenance_path.read_bytes() if provenance_path.is_file() else None
        provenance_change = old_provenance_bytes != provenance_bytes
        would_change = provenance_change or any(item["status"] != "no_change" for item in changes)

        plan = {
            "selected_skills": selected,
            "changes": changes,
            "provenance_change": provenance_change,
            "would_change": would_change,
            "force": bool(force),
            "dry_run": bool(dry_run),
        }
        if dry_run or not would_change:
            return {
                "ok": True,
                "action": "skill_sync",
                "status": "dry_run" if dry_run else "already_synced",
                "target_repo": str(target),
                "source_repo": str(source),
                "authority": {key: value for key, value in authority.items() if key != "record"},
                "plan": plan,
                "existing_managed_checks": existing_checks,
                "provenance_path": str(provenance_path),
                "provenance": new_provenance,
                "git_before": before_git,
                "git_after": before_git,
                "mutation_performed": False,
                "commit_performed": False,
            }

        pb_dir = target / ".promptbranch"
        skills_dir = target / SKILLS_REL
        pb_dir_existed = pb_dir.exists()
        skills_dir_existed = skills_dir.exists()
        pb_dir.mkdir(parents=True, exist_ok=True)
        skills_dir.mkdir(parents=True, exist_ok=True)
        transaction = pb_dir / f".skill-sync-transaction-{os.getpid()}"
        if transaction.exists():
            shutil.rmtree(transaction)
        stage_dir = transaction / "stage"
        backup_dir = transaction / "backup"
        stage_dir.mkdir(parents=True)
        backup_dir.mkdir(parents=True)
        for skill in selected:
            shutil.copytree(staged_roots[skill], stage_dir / skill)
        provenance_tmp = transaction / "promptbranch-skills.json"
        provenance_tmp.write_bytes(provenance_bytes)

        backed_up: list[str] = []
        installed: list[str] = []
        try:
            for skill in selected:
                destination = skills_dir / skill
                backup = backup_dir / skill
                if destination.exists():
                    os.replace(destination, backup)
                    backed_up.append(skill)
                os.replace(stage_dir / skill, destination)
                installed.append(skill)
            provenance_path.parent.mkdir(parents=True, exist_ok=True)
            os.replace(provenance_tmp, provenance_path)

            validations: dict[str, Any] = {}
            for skill in selected:
                validation = skill_validate(skill, repo_path=target)
                validations[skill] = validation
                if not validation.get("ok"):
                    raise SkillSyncError(f"target_skill_validation_failed:{skill}:{';'.join(validation.get('errors') or [])}")
            for skill in selected:
                actual = _tree_digest(skills_dir / skill)
                expected = installed_entries[skill]["installed_tree_sha256"]
                if actual != expected:
                    raise SkillSyncError(f"target_skill_digest_mismatch:{skill}:{expected}:{actual}")
        except Exception as exc:
            for skill in reversed(installed):
                destination = skills_dir / skill
                if destination.exists():
                    shutil.rmtree(destination)
            for skill in reversed(backed_up):
                destination = skills_dir / skill
                backup = backup_dir / skill
                if destination.exists():
                    shutil.rmtree(destination)
                if backup.exists():
                    os.replace(backup, destination)
            if old_provenance_bytes is None:
                provenance_path.unlink(missing_ok=True)
            else:
                provenance_path.write_bytes(old_provenance_bytes)
            shutil.rmtree(transaction, ignore_errors=True)
            if not skills_dir_existed and skills_dir.exists() and not any(skills_dir.iterdir()):
                skills_dir.rmdir()
            if not pb_dir_existed and pb_dir.exists() and not any(pb_dir.iterdir()):
                pb_dir.rmdir()
            return {
                "ok": False,
                "action": "skill_sync",
                "status": "transaction_rolled_back",
                "target_repo": str(target),
                "authority": {key: value for key, value in authority.items() if key != "record"},
                "plan": plan,
                "errors": [f"{type(exc).__name__}:{exc}"],
                "mutation_performed": True,
                "rollback_performed": True,
                "commit_performed": False,
            }

        shutil.rmtree(transaction, ignore_errors=True)
        after_git = _git_status(target)
        return {
            "ok": True,
            "action": "skill_sync",
            "status": "skills_synced",
            "target_repo": str(target),
            "source_repo": str(source),
            "authority": {key: value for key, value in authority.items() if key != "record"},
            "plan": plan,
            "existing_managed_checks": existing_checks,
            "provenance_path": str(provenance_path),
            "provenance": new_provenance,
            "validations": validations,
            "git_before": before_git,
            "git_after": after_git,
            "mutation_performed": True,
            "rollback_performed": False,
            "commit_performed": False,
        }
