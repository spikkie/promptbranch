from __future__ import annotations

import hashlib
import re
import shlex
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from promptbranch_scheduler import plan_operation_resources

SOURCE_QUEUE_SCHEMA = "promptbranch.source_queue"
SOURCE_QUEUE_SCHEMA_VERSION = "1.0"
SOURCE_MUTATION_OPERATIONS = {
    "add": "src_add",
    "sync": "src_sync",
    "remove": "src_remove",
    "rm": "src_remove",
}


@dataclass(frozen=True)
class SourceMutationRequest:
    requested_operation: str
    scheduler_operation: str
    workspace_url: str | None
    workspace_id: str | None
    account_id: str = "default"
    service_id: str = "default"
    repo_path: str | None = None
    source_kind: str | None = None
    file_path: str | None = None
    display_name: str | None = None
    source_name: str | None = None
    sync_path: str | None = None
    overwrite_existing: bool = True
    exact: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def workspace_id_from_url(workspace_url: str | None) -> str | None:
    if not workspace_url:
        return None
    if workspace_url.rstrip("/") == "https://chatgpt.com":
        return None
    parsed = urlparse(workspace_url)
    candidate = parsed.path.strip("/").split("/")
    for part in candidate:
        if part.startswith("g-p-") or part.startswith("g-"):
            return re.sub(r"[^A-Za-z0-9_.-]", "_", part)
    digest = hashlib.sha256(workspace_url.encode("utf-8")).hexdigest()[:16]
    return f"workspace-{digest}"


def workspace_url_from_state(state_snapshot: dict[str, Any] | None, override: str | None = None) -> str | None:
    if override:
        return override
    state = state_snapshot if isinstance(state_snapshot, dict) else {}
    for key in ("resolved_project_home_url", "project_home_url", "project_url"):
        value = state.get(key)
        if isinstance(value, str) and value.strip() and value.strip().rstrip("/") != "https://chatgpt.com":
            return value.strip()
    workspace = state.get("workspace") if isinstance(state.get("workspace"), dict) else {}
    for key in ("project_home_url", "project_url"):
        value = workspace.get(key)
        if isinstance(value, str) and value.strip() and value.strip().rstrip("/") != "https://chatgpt.com":
            return value.strip()
    return None


def normalize_source_operation(operation: str | None) -> tuple[str | None, str | None]:
    requested = (operation or "").strip().lower()
    if not requested:
        return None, None
    scheduler_operation = SOURCE_MUTATION_OPERATIONS.get(requested)
    return requested, scheduler_operation


def render_source_mutation_command(request: SourceMutationRequest) -> str:
    if request.requested_operation == "add":
        parts = ["pb", "src", "add"]
        if request.source_kind and request.source_kind != "file":
            parts += ["--type", shlex.quote(request.source_kind)]
        if request.file_path:
            parts += ["--file", shlex.quote(request.file_path)]
        if request.display_name:
            parts += ["--name", shlex.quote(request.display_name)]
        if not request.overwrite_existing:
            parts.append("--no-overwrite")
        parts.append("--json")
        return " ".join(parts)
    if request.requested_operation == "sync":
        parts = ["pb", "src", "sync", shlex.quote(request.sync_path or request.repo_path or ".")]
        parts += ["--upload", "--json"]
        return " ".join(parts)
    if request.requested_operation in {"remove", "rm"}:
        parts = ["pb", "src", "rm", shlex.quote(request.source_name or "<source-name>")]
        if request.exact:
            parts.append("--exact")
        parts.append("--json")
        return " ".join(parts)
    return "pb src <operation> --json"


def source_mutation_verification_plan(request: SourceMutationRequest) -> dict[str, Any]:
    expected_identity = request.display_name or (Path(request.file_path).name if request.file_path else None) or request.source_name
    if request.requested_operation == "sync":
        expected_identity = expected_identity or "generated source-sync artifact"
    return {
        "required": True,
        "sequence": [
            "capture_before_source_list_snapshot",
            "trigger_source_mutation_through_service_browser_queue",
            "wait_for_dialog_closed_sources_idle_add_button_visible_stability_dwell",
            "capture_after_source_list_snapshot",
            "verify_expected_source_delta",
            "verify_no_collateral_source_removal_or_replacement",
            "update_state_only_after_verified_readback",
        ],
        "expected_identity": expected_identity,
        "collateral_change_detection": True,
        "state_update_before_verification_allowed": False,
        "refresh_before_commit_stable_allowed": False,
    }


def build_source_mutation_queue_plan(
    *,
    operation: str,
    state_snapshot: dict[str, Any] | None = None,
    workspace_url: str | None = None,
    account_id: str = "default",
    service_id: str = "default",
    repo_path: str | None = None,
    source_kind: str | None = None,
    file_path: str | None = None,
    display_name: str | None = None,
    source_name: str | None = None,
    sync_path: str | None = None,
    overwrite_existing: bool = True,
    exact: bool = False,
) -> dict[str, Any]:
    requested_operation, scheduler_operation = normalize_source_operation(operation)
    if scheduler_operation is None:
        return {
            "ok": False,
            "action": "source_mutation_queue_plan",
            "status": "unknown_source_mutation_operation",
            "schema": f"{SOURCE_QUEUE_SCHEMA}.plan",
            "schema_version": SOURCE_QUEUE_SCHEMA_VERSION,
            "requested_operation": operation,
            "known_operations": sorted(SOURCE_MUTATION_OPERATIONS),
            "mutation_executed": False,
            "planning_only": True,
        }

    effective_workspace_url = workspace_url_from_state(state_snapshot, workspace_url)
    workspace_id = workspace_id_from_url(effective_workspace_url)
    request = SourceMutationRequest(
        requested_operation=requested_operation or operation,
        scheduler_operation=scheduler_operation,
        workspace_url=effective_workspace_url,
        workspace_id=workspace_id,
        account_id=account_id or "default",
        service_id=service_id or "default",
        repo_path=repo_path,
        source_kind=source_kind,
        file_path=file_path,
        display_name=display_name,
        source_name=source_name,
        sync_path=sync_path,
        overwrite_existing=overwrite_existing,
        exact=exact,
    )
    missing: list[str] = []
    if not workspace_id:
        missing.append("workspace_url")
    if scheduler_operation == "src_add" and source_kind == "file" and not file_path:
        missing.append("file_path")
    if scheduler_operation == "src_remove" and not source_name:
        missing.append("source_name")

    context = {
        "account_id": request.account_id,
        "project_id": workspace_id or "{project_id}",
        "service_id": request.service_id,
        "repo_path": repo_path or sync_path or ".",
    }
    resource_plan = plan_operation_resources(scheduler_operation, context)
    ok = not missing and bool(resource_plan.get("ok"))
    status = "planned" if ok else "missing_context"
    return {
        "ok": ok,
        "action": "source_mutation_queue_plan",
        "status": status,
        "schema": f"{SOURCE_QUEUE_SCHEMA}.plan",
        "schema_version": SOURCE_QUEUE_SCHEMA_VERSION,
        "requested_operation": request.requested_operation,
        "scheduler_operation": scheduler_operation,
        "planning_only": True,
        "mutation_executed": False,
        "project_source_mutated": False,
        "workspace": {
            "workspace_url": effective_workspace_url,
            "workspace_id": workspace_id,
            "lock_scope": f"sources:{workspace_id}" if workspace_id else None,
        },
        "request": request.to_dict(),
        "missing_context": sorted(set(missing) | set(resource_plan.get("missing_context", []))),
        "resource_plan": resource_plan,
        "queue_policy": {
            "queue_required": True,
            "per_workspace_source_mutations_serialized": True,
            "same_workspace_conflicts": ["src_add", "src_sync", "src_remove"],
            "different_workspace_parallel_allowed": True,
            "service_profile_exclusive": True,
            "transactional": True,
        },
        "verification_plan": source_mutation_verification_plan(request),
        "next_safe_commands": [
            "pb src list --json",
            render_source_mutation_command(request),
            "pb src list --json",
        ],
        "notes": "This is a source-mutation queue and verification plan only. It does not add, sync, or remove Project Sources.",
    }
