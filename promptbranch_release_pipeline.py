from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from promptbranch_application_architecture import (
    ApplicationArchitectureError,
    load_application_declaration,
    validate_application_architecture,
)
from promptbranch_application_migration import (
    ApplicationMigrationError,
    build_application_migration_report,
)
from promptbranch_release_engine import (
    ReleaseContractError,
    execute as execute_release_contract,
    load_contract,
    plan as plan_release_contract,
)

PIPELINE_SCHEMA = "promptbranch.release.pipeline"
PIPELINE_SCHEMA_VERSION = "1.0"
INVENTORY_SCHEMA = "promptbranch.pbai.compliance-inventory"
INVENTORY_SCHEMA_VERSION = "1.0"
CANONICAL_VERSION_RE = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+(?:\.[0-9]+)*")
LOCAL_OPERATIONS = ("validate", "test", "build", "verify")
DEFAULT_UNSAFE_GIT_PATTERNS = (
    ".env",
    ".generated/",
    ".pb_profile/",
    "debug_artifacts/",
    "*.zip",
    "*.log",
    "__pycache__/",
    ".pytest_cache/",
)


class ReleasePipelineError(ValueError):
    pass


Runner = Callable[..., subprocess.CompletedProcess[str]]


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_id(version: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{stamp}-{version.removeprefix('v')}"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleasePipelineError(f"invalid JSON evidence {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReleasePipelineError(f"JSON evidence root must be an object: {path}")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _canonical_version(repo: Path, contract: dict[str, Any]) -> str:
    version_path = repo / str(contract["version_authority"]["path"])
    try:
        value = version_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ReleasePipelineError(f"cannot read version authority {version_path}: {exc}") from exc
    if not CANONICAL_VERSION_RE.fullmatch(value):
        raise ReleasePipelineError(f"VERSION must be canonical and v-prefixed; got {value!r}")
    return value


def _artifact_path(repo: Path, contract: dict[str, Any]) -> Path:
    return (repo / str(contract["artifact"]["path"])).resolve()


def _path_matches(path_text: str, patterns: Sequence[str]) -> bool:
    normalized = path_text.strip().replace("\\", "/")
    for raw in patterns:
        pattern = str(raw or "").strip().replace("\\", "/").strip("/")
        if not pattern:
            continue
        if (
            fnmatch.fnmatch(normalized, pattern)
            or normalized == pattern
            or normalized.startswith(pattern.rstrip("/") + "/")
        ):
            return True
    return False


def _git_status(repo: Path, *, runner: Runner = subprocess.run) -> dict[str, Any]:
    try:
        result = runner(
            ["git", "status", "--porcelain=v1"],
            cwd=str(repo),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15.0,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "status": "git_status_error", "error": str(exc), "entries": []}
    if result.returncode != 0:
        return {
            "ok": False,
            "status": "git_status_error",
            "error": result.stderr.strip(),
            "entries": [],
        }
    entries: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        status = line[:2]
        path_text = line[3:].strip()
        if " -> " in path_text:
            path_text = path_text.split(" -> ", 1)[1].strip()
        entries.append({"status": status, "path": path_text})
    return {
        "ok": True,
        "status": "git_status_loaded",
        "entries": entries,
        "dirty_paths": [item["path"] for item in entries],
        "dirty": bool(entries),
    }


def _git_config(contract: dict[str, Any]) -> dict[str, Any]:
    configured = contract.get("git") if isinstance(contract.get("git"), dict) else {}
    unsafe = [str(value) for value in configured.get("unsafe_paths", DEFAULT_UNSAFE_GIT_PATTERNS)]
    expected = [str(value) for value in configured.get("expected_paths", [])]
    message = str(configured.get("commit_message") or "Release {version}")
    return {"unsafe_paths": unsafe, "expected_paths": expected, "commit_message": message}


def _git_stage_plan(repo: Path, contract: dict[str, Any], *, runner: Runner = subprocess.run) -> dict[str, Any]:
    status = _git_status(repo, runner=runner)
    cfg = _git_config(contract)
    entries = status.get("entries") if isinstance(status.get("entries"), list) else []
    dirty_paths = [str(item.get("path") or "") for item in entries if isinstance(item, dict)]
    unsafe = [path for path in dirty_paths if _path_matches(path, cfg["unsafe_paths"])]
    if cfg["expected_paths"]:
        allowed = [path for path in dirty_paths if _path_matches(path, cfg["expected_paths"])]
        unexpected = [path for path in dirty_paths if path not in allowed and path not in unsafe]
    else:
        allowed = [path for path in dirty_paths if path not in unsafe]
        unexpected = []
    ok = bool(status.get("ok")) and not unsafe and not unexpected
    return {
        "ok": ok,
        "status": "safe_to_stage" if ok else "unsafe_or_unexpected_dirty_paths",
        "git_status": status,
        "paths_to_stage": allowed,
        "unsafe_dirty_paths": unsafe,
        "unexpected_dirty_paths": unexpected,
        "unsafe_patterns": cfg["unsafe_paths"],
        "expected_patterns": cfg["expected_paths"],
    }


def _command_result(
    argv: Sequence[str],
    *,
    repo: Path,
    evidence_path: Path,
    timeout: float,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    started_at = _utc()
    try:
        result = runner(
            list(argv),
            cwd=str(repo),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        payload = {
            "ok": False,
            "status": "command_timeout",
            "argv": list(argv),
            "started_at": started_at,
            "finished_at": _utc(),
            "timeout_seconds": timeout,
            "stdout": exc.stdout if isinstance(exc.stdout, str) else "",
            "stderr": exc.stderr if isinstance(exc.stderr, str) else "",
        }
        _write_json(evidence_path, payload)
        return payload
    except OSError as exc:
        payload = {
            "ok": False,
            "status": "command_execution_error",
            "argv": list(argv),
            "started_at": started_at,
            "finished_at": _utc(),
            "error": str(exc),
        }
        _write_json(evidence_path, payload)
        return payload
    parsed: dict[str, Any] | None = None
    if result.stdout.strip():
        try:
            candidate = json.loads(result.stdout)
            if isinstance(candidate, dict):
                parsed = candidate
        except json.JSONDecodeError:
            parsed = None
    ok = result.returncode == 0 and (parsed is None or parsed.get("ok", True) is True)
    payload = {
        "ok": ok,
        "status": (parsed or {}).get("status") or ("command_passed" if ok else "command_failed"),
        "argv": list(argv),
        "started_at": started_at,
        "finished_at": _utc(),
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "payload": parsed,
    }
    _write_json(evidence_path, payload)
    return payload


def _pb_command() -> list[str]:
    override = str(os.environ.get("PROMPTBRANCH_PIPELINE_PB_COMMAND") or "").strip()
    if override:
        return [override]
    return [sys.executable, "-m", "promptbranch.cli"]


def _pipeline_dependencies(
    *,
    commit: bool,
    push: bool,
    publish: bool,
    adopt: bool,
    verify_current: bool,
    stage_all: bool,
) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    if commit and not stage_all:
        blockers.append({"code": "pipeline_commit_requires_stage_all", "message": "--commit requires explicit --stage-all"})
    if push and not commit:
        blockers.append({"code": "pipeline_push_requires_commit", "message": "--push requires --commit in the same pipeline run"})
    if publish and not push:
        blockers.append({"code": "pipeline_publish_requires_push", "message": "--publish requires a successful same-run --push"})
    if adopt and not publish:
        blockers.append({"code": "pipeline_adopt_requires_publish", "message": "--adopt requires same-run Project Source publication"})
    if verify_current and not adopt:
        blockers.append({"code": "pipeline_verify_current_requires_adopt", "message": "--verify-current requires same-run adoption"})
    return blockers


def build_release_pipeline_plan(
    repo_path: str | Path = ".",
    *,
    config: str = ".promptbranch-release.json",
    confirm_version: str | None = None,
    stage_all: bool = False,
    commit: bool = False,
    push: bool = False,
    publish: bool = False,
    adopt: bool = False,
    verify_current: bool = False,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    repo = Path(repo_path).expanduser().resolve()
    blockers = _pipeline_dependencies(
        commit=commit,
        push=push,
        publish=publish,
        adopt=adopt,
        verify_current=verify_current,
        stage_all=stage_all,
    )
    try:
        contract = load_contract(repo, config)
        version = _canonical_version(repo, contract)
    except (ReleaseContractError, ReleasePipelineError) as exc:
        return {
            "ok": False,
            "schema": PIPELINE_SCHEMA,
            "schema_version": PIPELINE_SCHEMA_VERSION,
            "action": "release_pipeline_plan",
            "status": "pipeline_contract_invalid",
            "repo_path": str(repo),
            "blockers": [{"code": "pipeline_contract_invalid", "message": str(exc)}],
            "safety": {"read_only": True, "state_mutated": False},
        }
    if confirm_version is not None and str(confirm_version).strip() != version:
        blockers.append({
            "code": "pipeline_confirm_version_mismatch",
            "message": f"--confirm-version must equal {version}",
        })
    artifact = _artifact_path(repo, contract)
    git_plan = _git_stage_plan(repo, contract, runner=runner)
    if commit and not git_plan.get("ok"):
        blockers.append({
            "code": "pipeline_git_stage_blocked",
            "message": "Git staging preflight is not safe",
        })
    contract_plan = plan_release_contract(repo, contract)
    phases = [
        {"id": "local_validate", "operation": "validate", "enabled": True, "mutating": False},
        {"id": "local_test", "operation": "test", "enabled": True, "mutating": False},
        {"id": "local_build", "operation": "build", "enabled": True, "mutating": True},
        {"id": "local_verify", "operation": "verify", "enabled": True, "mutating": False},
        {"id": "git_commit", "operation": "git_commit", "enabled": commit, "mutating": commit},
        {"id": "git_push", "operation": "git_push", "enabled": push, "mutating": push},
        {"id": "committed_tree_rebuild", "operation": "build", "enabled": commit, "mutating": commit},
        {"id": "committed_tree_reverify", "operation": "verify", "enabled": commit, "mutating": False},
        {"id": "project_source_publish", "operation": "publish", "enabled": publish, "mutating": publish},
        {"id": "artifact_adopt", "operation": "adopt", "enabled": adopt, "mutating": adopt},
        {"id": "accepted_current_verify", "operation": "verify_current", "enabled": verify_current, "mutating": False},
    ]
    return {
        "ok": not blockers,
        "schema": PIPELINE_SCHEMA,
        "schema_version": PIPELINE_SCHEMA_VERSION,
        "action": "release_pipeline_plan",
        "status": "pipeline_planned_read_only" if not blockers else "pipeline_plan_blocked",
        "repo_path": str(repo),
        "repository": contract["repository"],
        "version": version,
        "confirmed_version": confirm_version,
        "artifact": {"path": str(artifact), "filename": artifact.name, "exists": artifact.is_file()},
        "contract_plan": contract_plan,
        "phases": phases,
        "git_stage_plan": git_plan,
        "requested_mutations": {
            "stage_all": stage_all,
            "commit": commit,
            "push": push,
            "publish": publish,
            "adopt": adopt,
            "verify_current": verify_current,
        },
        "blockers": blockers,
        "blocker_codes": [item["code"] for item in blockers],
        "safety": {
            "read_only": True,
            "state_mutated": False,
            "publication_separate": True,
            "adoption_requires_source_evidence": True,
            "accepted_current_verification_separate": True,
        },
    }


def _record_phase(evidence_dir: Path, phase_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    path = evidence_dir / f"{phase_id}.json"
    _write_json(path, payload)
    return {
        "phase": phase_id,
        "ok": bool(payload.get("ok")),
        "status": payload.get("status"),
        "evidence_path": str(path),
        "payload": payload,
    }


def _run_git_commit_push(
    repo: Path,
    contract: dict[str, Any],
    *,
    version: str,
    message: str | None,
    push: bool,
    evidence_dir: Path,
    runner: Runner,
) -> dict[str, Any]:
    plan = _git_stage_plan(repo, contract, runner=runner)
    if not plan.get("ok"):
        return {
            "ok": False,
            "status": "git_stage_preflight_blocked",
            "git_stage_plan": plan,
            "commit_performed": False,
            "push_performed": False,
        }
    paths = [str(value) for value in plan.get("paths_to_stage", []) if str(value).strip()]
    if not paths:
        return {
            "ok": False,
            "status": "git_commit_no_changes",
            "git_stage_plan": plan,
            "commit_performed": False,
            "push_performed": False,
        }
    stage = _command_result(
        ["git", "add", "--", *paths],
        repo=repo,
        evidence_path=evidence_dir / "git-stage-command.json",
        timeout=60.0,
        runner=runner,
    )
    if not stage.get("ok"):
        return {"ok": False, "status": "git_stage_failed", "git_stage": stage, "commit_performed": False, "push_performed": False}
    template = _git_config(contract)["commit_message"]
    commit_message = message or template.replace("{version}", version)
    commit = _command_result(
        ["git", "commit", "-m", commit_message],
        repo=repo,
        evidence_path=evidence_dir / "git-commit-command.json",
        timeout=120.0,
        runner=runner,
    )
    if not commit.get("ok"):
        return {"ok": False, "status": "git_commit_failed", "git_stage": stage, "git_commit": commit, "commit_performed": False, "push_performed": False}
    push_result: dict[str, Any] | None = None
    if push:
        push_result = _command_result(
            ["git", "push"],
            repo=repo,
            evidence_path=evidence_dir / "git-push-command.json",
            timeout=180.0,
            runner=runner,
        )
        if not push_result.get("ok"):
            return {
                "ok": False,
                "status": "git_push_failed",
                "git_stage": stage,
                "git_commit": commit,
                "git_push": push_result,
                "commit_performed": True,
                "push_performed": False,
            }
    return {
        "ok": True,
        "status": "git_committed_and_pushed" if push else "git_committed",
        "git_stage_plan": plan,
        "git_stage": stage,
        "git_commit": commit,
        "git_push": push_result,
        "commit_performed": True,
        "push_performed": push,
    }


def execute_release_pipeline(
    repo_path: str | Path = ".",
    *,
    config: str = ".promptbranch-release.json",
    confirm_version: str,
    stage_all: bool = False,
    commit: bool = False,
    push: bool = False,
    publish: bool = False,
    adopt: bool = False,
    verify_current: bool = False,
    message: str | None = None,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    repo = Path(repo_path).expanduser().resolve()
    plan = build_release_pipeline_plan(
        repo,
        config=config,
        confirm_version=confirm_version,
        stage_all=stage_all,
        commit=commit,
        push=push,
        publish=publish,
        adopt=adopt,
        verify_current=verify_current,
        runner=runner,
    )
    if not plan.get("ok"):
        return {
            **plan,
            "action": "release_pipeline_apply",
            "status": "pipeline_apply_blocked",
            "applied": False,
            "mutating_actions_executed": False,
        }
    contract = load_contract(repo, config)
    version = str(plan["version"])
    artifact = _artifact_path(repo, contract)
    repo_id = str(contract["repository"]["repo_id"])
    evidence_dir = repo / str(contract["evidence"]["directory"]) / "pipeline" / _run_id(version)
    evidence_dir.mkdir(parents=True, exist_ok=False)
    phases: list[dict[str, Any]] = []
    stop_reason: str | None = None

    def run_local(phase_id: str, operation: str) -> bool:
        nonlocal stop_reason
        payload = execute_release_contract(repo, contract, operation)
        phases.append(_record_phase(evidence_dir, phase_id, payload))
        if not payload.get("ok"):
            stop_reason = f"{phase_id}_failed"
            return False
        return True

    for phase_id, operation in (
        ("local-validate", "validate"),
        ("local-test", "test"),
        ("local-build", "build"),
        ("local-verify", "verify"),
    ):
        if not run_local(phase_id, operation):
            break

    if stop_reason is None and commit:
        git_payload = _run_git_commit_push(
            repo,
            contract,
            version=version,
            message=message,
            push=push,
            evidence_dir=evidence_dir,
            runner=runner,
        )
        phases.append(_record_phase(evidence_dir, "git-sync", git_payload))
        if not git_payload.get("ok"):
            stop_reason = "git_sync_failed"

    if stop_reason is None and commit:
        if not run_local("committed-tree-build", "build"):
            stop_reason = "committed_tree_build_failed"
        elif not run_local("committed-tree-verify", "verify"):
            stop_reason = "committed_tree_verify_failed"

    source_evidence_path = evidence_dir / "project-source-add.json"
    source_payload: dict[str, Any] | None = None
    if stop_reason is None and publish:
        source_command = [*_pb_command(), "src", "add", str(artifact), "--no-overwrite", "--json"]
        source_result = _command_result(
            source_command,
            repo=repo,
            evidence_path=evidence_dir / "project-source-add-command.json",
            timeout=1200.0,
            runner=runner,
        )
        source_payload = source_result.get("payload") if isinstance(source_result.get("payload"), dict) else None
        if source_payload is not None:
            _write_json(source_evidence_path, source_payload)
        required_source = bool(
            source_result.get("ok")
            and source_payload
            and source_payload.get("ok") is True
            and source_payload.get("persistence_verified") is True
            and source_payload.get("assigned_filename")
            and source_payload.get("processed_file_id")
            and source_payload.get("library_metadata_object_id")
        )
        publish_payload = {
            "ok": required_source,
            "status": "project_source_published" if required_source else "project_source_publication_unverified",
            "command_result": source_result,
            "source_evidence_path": str(source_evidence_path) if source_payload is not None else None,
            "source": source_payload,
        }
        phases.append(_record_phase(evidence_dir, "project-source-publish", publish_payload))
        if not publish_payload.get("ok"):
            stop_reason = "project_source_publish_failed"

    adoption_payload: dict[str, Any] | None = None
    if stop_reason is None and adopt:
        adopt_command = [
            *_pb_command(),
            "artifact",
            "adopt",
            artifact.name,
            "--from-project-source",
            "--local-path",
            str(artifact),
            "--repo",
            repo_id,
            "--source-evidence-json",
            str(source_evidence_path),
            "--json",
        ]
        adoption_result = _command_result(
            adopt_command,
            repo=repo,
            evidence_path=evidence_dir / "artifact-adopt-command.json",
            timeout=1200.0,
            runner=runner,
        )
        adoption_payload = adoption_result.get("payload") if isinstance(adoption_result.get("payload"), dict) else None
        adoption_verified = bool(
            adoption_result.get("ok")
            and adoption_payload
            and adoption_payload.get("ok") is True
            and adoption_payload.get("status") == "adopted"
            and adoption_payload.get("source_verified") is True
            and adoption_payload.get("source_evidence_verified") is True
            and adoption_payload.get("artifact_registry_updated") is True
            and adoption_payload.get("state_artifact_updated") is True
            and adoption_payload.get("state_source_updated") is True
        )
        phase_payload = {
            "ok": adoption_verified,
            "status": "artifact_adopted" if adoption_verified else "artifact_adoption_unverified",
            "command_result": adoption_result,
            "adoption": adoption_payload,
        }
        phases.append(_record_phase(evidence_dir, "artifact-adopt", phase_payload))
        if not phase_payload.get("ok"):
            stop_reason = "artifact_adopt_failed"

    current_payload: dict[str, Any] | None = None
    if stop_reason is None and verify_current:
        current_result = _command_result(
            [*_pb_command(), "artifact", "current", "--all", "--json"],
            repo=repo,
            evidence_path=evidence_dir / "artifact-current-command.json",
            timeout=180.0,
            runner=runner,
        )
        current_payload = current_result.get("payload") if isinstance(current_result.get("payload"), dict) else None
        selected_repo = ((current_payload or {}).get("repos") or {}).get(repo_id) or {}
        repo_state = selected_repo.get("state") or {}
        registry_current = selected_repo.get("registry_current") or {}
        consistency = selected_repo.get("consistency") or {}
        expected_source_ref = str((source_payload or {}).get("assigned_filename") or "")
        current_verified = bool(
            current_result.get("ok")
            and current_payload
            and current_payload.get("ok") is True
            and current_payload.get("missing_repo_count", 0) == 0
            and selected_repo.get("ok", True) is True
            and repo_state.get("artifact_ref") == artifact.name
            and repo_state.get("artifact_version") == version
            and repo_state.get("source_ref") == expected_source_ref
            and repo_state.get("source_version") == version
            and registry_current.get("filename") == artifact.name
            and registry_current.get("version") == version
            and consistency.get("registry_current_matches_state_artifact") is True
            and consistency.get("state_source_matches_state_artifact") is True
        )
        phase_payload = {
            "ok": current_verified,
            "status": "accepted_current_verified" if current_verified else "accepted_current_mismatch",
            "command_result": current_result,
            "current": current_payload,
            "expected_source_ref": expected_source_ref,
            "selected_repo_state": repo_state,
            "selected_registry_current": registry_current,
            "selected_consistency": consistency,
        }
        phases.append(_record_phase(evidence_dir, "accepted-current-verify", phase_payload))
        if not phase_payload.get("ok"):
            stop_reason = "accepted_current_verify_failed"

    final_ok = stop_reason is None
    summary = {
        "ok": final_ok,
        "schema": PIPELINE_SCHEMA,
        "schema_version": PIPELINE_SCHEMA_VERSION,
        "action": "release_pipeline_apply",
        "status": "release_pipeline_completed" if final_ok else "release_pipeline_failed",
        "repo_path": str(repo),
        "repository": contract["repository"],
        "version": version,
        "artifact": {"path": str(artifact), "filename": artifact.name, "exists": artifact.is_file()},
        "evidence_dir": str(evidence_dir),
        "phase_results": phases,
        "phase_count": len(phases),
        "stop_reason": stop_reason,
        "commit_requested": commit,
        "push_requested": push,
        "publish_requested": publish,
        "adopt_requested": adopt,
        "verify_current_requested": verify_current,
        "source_evidence_path": str(source_evidence_path) if source_payload is not None else None,
        "source": source_payload,
        "adoption": adoption_payload,
        "current": current_payload,
        "mutating_actions_executed": any(
            bool((item.get("payload") or {}).get("commit_performed"))
            or item.get("phase") in {"local-build", "committed-tree-build", "project-source-publish", "artifact-adopt"}
            for item in phases
        ),
        "safety": {
            "explicit_version_confirmation": True,
            "publication_after_push": not publish or push,
            "adoption_evidence_bound": not adopt or source_payload is not None,
            "accepted_current_verified": not verify_current or final_ok,
            "later_phases_skipped_after_failure": True,
        },
    }
    _write_json(evidence_dir / "release-pipeline-summary.json", summary)
    return summary


def build_pbai_compliance_inventory(
    repo_paths: Sequence[str | Path],
    *,
    level: str = "executable",
    config: str = ".promptbranch-ai.json",
    release_config: str = ".promptbranch-release.json",
) -> dict[str, Any]:
    repositories: list[dict[str, Any]] = []
    for value in repo_paths:
        repo = Path(value).expanduser().resolve()
        item: dict[str, Any] = {
            "repo_path": str(repo),
            "exists": repo.is_dir(),
            "application_id": None,
            "application_kind": None,
            "version": None,
            "migration": None,
            "validation": None,
            "release_contract": None,
            "rollout_ready": False,
            "errors": [],
        }
        if not repo.is_dir():
            item["errors"].append("repository path not found")
            repositories.append(item)
            continue
        declaration: dict[str, Any] | None = None
        try:
            declaration = load_application_declaration(repo, config)
            application = declaration.get("application") if isinstance(declaration.get("application"), dict) else {}
            item["application_id"] = application.get("id")
            item["application_kind"] = application.get("kind")
            authority = declaration.get("version_authority") if isinstance(declaration.get("version_authority"), dict) else {}
            version_path = repo / str(authority.get("path") or "VERSION")
            if version_path.is_file():
                item["version"] = version_path.read_text(encoding="utf-8").strip()
        except (ApplicationArchitectureError, OSError) as exc:
            item["errors"].append(str(exc))
        try:
            item["migration"] = build_application_migration_report(
                repo,
                kind=item.get("application_kind") or "domain_module",
                application_id=item.get("application_id") or repo.name.replace("_", "-"),
                config=config,
            )
        except ApplicationMigrationError as exc:
            item["errors"].append(str(exc))
        try:
            item["validation"] = validate_application_architecture(repo, config, level=level)
        except (ApplicationArchitectureError, OSError, ValueError) as exc:
            item["errors"].append(str(exc))
            item["validation"] = {
                "ok": False,
                "status": "application_validation_failed",
                "error": str(exc),
            }
        try:
            release_contract = load_contract(repo, release_config)
            item["release_contract"] = plan_release_contract(repo, release_contract)
        except (ReleaseContractError, OSError, ValueError) as exc:
            item["errors"].append(str(exc))
            item["release_contract"] = {
                "ok": False,
                "status": "release_contract_invalid",
                "error": str(exc),
            }
        item["rollout_ready"] = bool(
            (item.get("migration") or {}).get("status") == "already_migrated"
            and (item.get("validation") or {}).get("ok") is True
            and (item.get("release_contract") or {}).get("ok") is True
        )
        repositories.append(item)
    ready_count = sum(1 for item in repositories if item.get("rollout_ready"))
    return {
        "ok": all(item.get("exists") for item in repositories),
        "schema": INVENTORY_SCHEMA,
        "schema_version": INVENTORY_SCHEMA_VERSION,
        "action": "pbai_compliance_inventory",
        "status": "inventory_complete",
        "requested_level": level,
        "repository_count": len(repositories),
        "rollout_ready_count": ready_count,
        "blocked_count": len(repositories) - ready_count,
        "repositories": repositories,
        "safety": {
            "read_only": True,
            "state_mutated": False,
            "publication_performed": False,
            "adoption_performed": False,
        },
    }
