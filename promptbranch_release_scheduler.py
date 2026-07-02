from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from promptbranch_scheduler import conflict_matrix, plan_operation_resources
from promptbranch_source_queue import build_source_mutation_queue_plan, workspace_id_from_url, workspace_url_from_state

RELEASE_SCHEDULER_SCHEMA = "promptbranch.release_scheduler"
RELEASE_SCHEDULER_SCHEMA_VERSION = "1.0"


def _safe_id(value: str | None, *, fallback: str) -> str:
    text = (value or "").strip()
    if not text:
        return fallback
    normalized = re.sub(r"[^A-Za-z0-9_.-]", "_", text)
    normalized = normalized.strip("._-")
    if normalized:
        return normalized[:96]
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"{fallback}-{digest}"


def repo_id_from_path(repo_path: str | Path | None) -> str:
    repo = Path(repo_path or ".").expanduser().resolve()
    return _safe_id(repo.name, fallback="repo")


def artifact_display_name(artifact_path: str | Path | None) -> str | None:
    if not artifact_path:
        return None
    return Path(str(artifact_path)).name


@dataclass(frozen=True)
class ReleaseLifecycleSchedulerRequest:
    artifact_path: str | None
    artifact_version: str | None
    target_version: str | None
    repo_path: str
    repo_id: str
    workspace_url: str | None
    workspace_id: str | None
    account_id: str = "default"
    service_id: str = "default"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def release_lifecycle_phase_plan(*, artifact_path: str | None, version: str | None, target_version: str | None) -> list[dict[str, Any]]:
    artifact = artifact_path or "<artifact.zip>"
    release_version = version or "<version>"
    next_version = target_version or ""
    return [
        {
            "phase": "doctor",
            "scheduler_operation": "release_doctor",
            "resource_role": "read_precheck",
            "command": f"pb release doctor --artifact {artifact} --version {release_version} --target-version {next_version} --json".strip(),
            "mutates": False,
            "queue_required": False,
        },
        {
            "phase": "install",
            "scheduler_operation": "release_lifecycle",
            "resource_role": "repo_artifact_write",
            "command": f"pb release install --artifact {artifact} --version {release_version} --target-version {next_version} --upload-source --json".strip(),
            "mutates": True,
            "queue_required": True,
        },
        {
            "phase": "source_upload",
            "scheduler_operation": "src_add",
            "resource_role": "project_source_write",
            "command": f"pb src add --file {artifact} --name {Path(artifact).name if artifact != '<artifact.zip>' else '<artifact.zip>'} --json".strip(),
            "mutates": True,
            "queue_required": True,
        },
        {
            "phase": "acceptance_hooks",
            "scheduler_operation": "release_lifecycle",
            "resource_role": "repo_process_gate",
            "command": f"pb release test --artifact {artifact} --version {release_version} --target-version {next_version} --json".strip(),
            "mutates": False,
            "queue_required": True,
        },
        {
            "phase": "adopt",
            "scheduler_operation": "artifact_adopt",
            "resource_role": "artifact_state_write",
            "command": f"pb release adopt --artifact {artifact} --version {release_version} --target-version {next_version} --json".strip(),
            "mutates": True,
            "queue_required": True,
        },
        {
            "phase": "policy_sync",
            "scheduler_operation": "release_lifecycle",
            "resource_role": "policy_write",
            "command": f"pb release policy-sync --artifact {artifact} --version {release_version} --target-version {next_version} --json".strip(),
            "mutates": True,
            "queue_required": True,
        },
        {
            "phase": "git_sync",
            "scheduler_operation": "release_lifecycle",
            "resource_role": "repo_git_write_optional",
            "command": f"pb release git-sync --artifact {artifact} --version {release_version} --target-version {next_version} --plan --json".strip(),
            "mutates": False,
            "queue_required": True,
        },
    ]


def build_release_lifecycle_scheduler_plan(
    *,
    artifact_path: str | Path | None,
    artifact_version: str | None,
    target_version: str | None = None,
    repo_path: str | Path = ".",
    state_snapshot: dict[str, Any] | None = None,
    workspace_url: str | None = None,
    account_id: str = "default",
    service_id: str = "default",
    repo_id: str | None = None,
) -> dict[str, Any]:
    repo = Path(repo_path or ".").expanduser().resolve()
    effective_workspace_url = workspace_url_from_state(state_snapshot, workspace_url)
    workspace_id = workspace_id_from_url(effective_workspace_url)
    resolved_repo_id = repo_id or repo_id_from_path(repo)
    artifact_str = str(artifact_path) if artifact_path else None
    artifact_name = artifact_display_name(artifact_str)

    context = {
        "account_id": account_id or "default",
        "project_id": workspace_id or "{project_id}",
        "service_id": service_id or "default",
        "repo_path": str(repo),
        "repo_id": resolved_repo_id,
    }
    lifecycle_resource_plan = plan_operation_resources("release_lifecycle", context)
    source_upload_queue_plan = build_source_mutation_queue_plan(
        operation="add",
        state_snapshot=state_snapshot,
        workspace_url=effective_workspace_url,
        account_id=account_id or "default",
        service_id=service_id or "default",
        repo_path=str(repo),
        source_kind="file",
        file_path=artifact_str,
        display_name=artifact_name,
        overwrite_existing=True,
    )
    source_conflict_plan = conflict_matrix("release_lifecycle", "src_add", context)
    artifact_conflict_plan = conflict_matrix("release_lifecycle", "artifact_adopt", context)

    missing_context = sorted(
        set(lifecycle_resource_plan.get("missing_context", []))
        | set(source_upload_queue_plan.get("missing_context", []))
    )
    ok = not missing_context and bool(lifecycle_resource_plan.get("ok")) and bool(source_upload_queue_plan.get("ok"))

    return {
        "ok": ok,
        "action": "release_lifecycle_scheduler_plan",
        "status": "planned" if ok else "missing_context",
        "schema": f"{RELEASE_SCHEDULER_SCHEMA}.plan",
        "schema_version": RELEASE_SCHEDULER_SCHEMA_VERSION,
        "planning_only": True,
        "mutation_executed": False,
        "project_source_mutated": False,
        "artifact_registry_updated": False,
        "state_updated": False,
        "request": ReleaseLifecycleSchedulerRequest(
            artifact_path=artifact_str,
            artifact_version=artifact_version,
            target_version=target_version,
            repo_path=str(repo),
            repo_id=resolved_repo_id,
            workspace_url=effective_workspace_url,
            workspace_id=workspace_id,
            account_id=account_id or "default",
            service_id=service_id or "default",
        ).to_dict(),
        "missing_context": missing_context,
        "workspace": {
            "workspace_url": effective_workspace_url,
            "workspace_id": workspace_id,
            "source_lock_scope": f"sources:{workspace_id}" if workspace_id else None,
        },
        "resource_plan": lifecycle_resource_plan,
        "source_upload_queue_plan": source_upload_queue_plan,
        "conflict_checks": {
            "release_lifecycle_vs_src_add": source_conflict_plan,
            "release_lifecycle_vs_artifact_adopt": artifact_conflict_plan,
        },
        "queue_policy": {
            "release_lifecycle_queue_required": True,
            "per_repo_lifecycle_serialized": True,
            "per_workspace_source_upload_serialized": True,
            "source_upload_uses_source_queue_plan": True,
            "same_workspace_source_mutations_conflict": True,
            "same_repo_artifact_adoption_conflicts": True,
            "different_workspace_parallel_allowed_after_repo_lock_is_distinct": True,
            "service_profile_exclusive": True,
            "transactional": True,
        },
        "phase_plan": release_lifecycle_phase_plan(
            artifact_path=artifact_str,
            version=artifact_version,
            target_version=target_version,
        ),
        "verification_plan": {
            "required": True,
            "sequence": [
                "verify_candidate_zip_before_queue_entry",
                "capture_pre_lifecycle_artifact_current",
                "capture_pre_lifecycle_project_source_list",
                "acquire_release_lifecycle_repo_and_artifact_locks",
                "delegate_project_source_upload_to_source_queue_plan",
                "run_acceptance_hooks_before_adoption",
                "adopt_artifact_only_after_green_acceptance",
                "sync_policy_only_after_adoption_verified",
                "capture_post_lifecycle_artifact_current",
                "capture_post_lifecycle_project_source_list",
                "verify_no_collateral_source_change",
            ],
            "state_update_before_verification_allowed": False,
            "project_source_upload_without_source_queue_allowed": False,
            "git_commit_without_policy_sync_allowed": False,
        },
        "operator_instruction": "Read-only scheduler integration plan. No install, source upload, hooks, adoption, policy sync, git commit, or git push was executed.",
    }
