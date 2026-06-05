from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from promptbranch_parallel import OPERATION_CLASSES, PARALLEL_ARCHITECTURE_VERSION, command_classification

SCHEDULER_SCHEMA = "promptbranch.scheduler"
SCHEDULER_SCHEMA_VERSION = "1.0"
DEFAULT_QUEUE_DIRNAME = ".pb_profile/queue"


@dataclass(frozen=True)
class PlannedResource:
    template: str
    resource: str
    scope: str
    mode: str
    missing_context: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["missing_context"] = list(self.missing_context)
        return payload


def _queue_dir(repo_path: str | Path = ".") -> Path:
    return Path(repo_path).expanduser().resolve() / DEFAULT_QUEUE_DIRNAME


def _known_placeholders(template: str) -> list[str]:
    names: list[str] = []
    start = 0
    while True:
        open_idx = template.find("{", start)
        if open_idx < 0:
            break
        close_idx = template.find("}", open_idx + 1)
        if close_idx < 0:
            break
        names.append(template[open_idx + 1 : close_idx])
        start = close_idx + 1
    return names


def _render_template(template: str, context: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    rendered = template
    missing: list[str] = []
    for name in _known_placeholders(template):
        if name not in context or context[name] in (None, ""):
            missing.append(name)
            continue
        rendered = rendered.replace("{" + name + "}", str(context[name]))
    return rendered, tuple(missing)


def _split_resource(resource: str) -> tuple[str, str]:
    parts = resource.split(":")
    if len(parts) >= 2 and parts[-1] in {"read", "write", "exclusive"}:
        return ":".join(parts[:-1]), parts[-1]
    return resource, "exclusive"


def _resources_conflict(left: PlannedResource, right: PlannedResource) -> bool:
    if left.scope != right.scope:
        return False
    if left.mode == "read" and right.mode == "read":
        return False
    return True


def plan_operation_resources(operation: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = dict(context or {})
    classification = command_classification(operation)
    if not classification.get("ok"):
        return {
            "ok": False,
            "action": "queue_plan",
            "status": "unknown_operation",
            "schema": f"{SCHEDULER_SCHEMA}.plan",
            "schema_version": SCHEDULER_SCHEMA_VERSION,
            "operation": operation,
            "known_operations": sorted(OPERATION_CLASSES),
        }

    operation_payload = classification["operation"]
    resources: list[PlannedResource] = []
    missing_context: set[str] = set()
    for template in operation_payload.get("resource_templates", []):
        rendered, missing = _render_template(str(template), context)
        scope, mode = _split_resource(rendered)
        missing_context.update(missing)
        resources.append(
            PlannedResource(
                template=str(template),
                resource=rendered,
                scope=scope,
                mode=mode,
                missing_context=missing,
            )
        )

    return {
        "ok": not missing_context,
        "action": "queue_plan",
        "status": "planned" if not missing_context else "missing_context",
        "schema": f"{SCHEDULER_SCHEMA}.plan",
        "schema_version": SCHEDULER_SCHEMA_VERSION,
        "operation": operation,
        "classification": operation_payload,
        "context": context,
        "missing_context": sorted(missing_context),
        "resource_count": len(resources),
        "resources": [resource.to_dict() for resource in resources],
        "queue_required": bool(operation_payload.get("queue_required")),
        "transactional": bool(operation_payload.get("transactional")),
    }


def conflict_matrix(left_operation: str, right_operation: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    left = plan_operation_resources(left_operation, context)
    right = plan_operation_resources(right_operation, context)
    conflicts: list[dict[str, Any]] = []
    if left.get("resources") and right.get("resources"):
        left_resources = [
            PlannedResource(
                template=item["template"],
                resource=item["resource"],
                scope=item["scope"],
                mode=item["mode"],
                missing_context=tuple(item.get("missing_context", [])),
            )
            for item in left["resources"]
        ]
        right_resources = [
            PlannedResource(
                template=item["template"],
                resource=item["resource"],
                scope=item["scope"],
                mode=item["mode"],
                missing_context=tuple(item.get("missing_context", [])),
            )
            for item in right["resources"]
        ]
        for l_resource in left_resources:
            for r_resource in right_resources:
                if _resources_conflict(l_resource, r_resource):
                    conflicts.append(
                        {
                            "left": l_resource.to_dict(),
                            "right": r_resource.to_dict(),
                            "scope": l_resource.scope,
                        }
                    )
    return {
        "ok": bool(left.get("ok") and right.get("ok")),
        "action": "queue_conflicts",
        "status": "conflict" if conflicts else "compatible",
        "schema": f"{SCHEDULER_SCHEMA}.conflicts",
        "schema_version": SCHEDULER_SCHEMA_VERSION,
        "left_operation": left_operation,
        "right_operation": right_operation,
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "left_plan_status": left.get("status"),
        "right_plan_status": right.get("status"),
        "missing_context": sorted(set(left.get("missing_context", [])) | set(right.get("missing_context", []))),
    }


def queue_status(repo_path: str | Path = ".") -> dict[str, Any]:
    repo = Path(repo_path).expanduser().resolve()
    queue_dir = _queue_dir(repo)
    operation_log = queue_dir / "operations.jsonl"
    active_count = 0
    queued_count = 0
    completed_count = 0
    if operation_log.exists():
        for line in operation_log.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            status = item.get("status")
            if status == "active":
                active_count += 1
            elif status == "queued":
                queued_count += 1
            elif status in {"completed", "failed", "cancelled"}:
                completed_count += 1
    return {
        "ok": True,
        "action": "queue_status",
        "status": "ready",
        "schema": f"{SCHEDULER_SCHEMA}.status",
        "schema_version": SCHEDULER_SCHEMA_VERSION,
        "architecture_version": PARALLEL_ARCHITECTURE_VERSION,
        "repo_path": str(repo),
        "queue_dir": str(queue_dir),
        "operation_log": str(operation_log),
        "operation_log_exists": operation_log.exists(),
        "active_count": active_count,
        "queued_count": queued_count,
        "completed_count": completed_count,
        "known_operation_count": len(OPERATION_CLASSES),
        "known_operations": sorted(OPERATION_CLASSES),
        "runtime_integration": "inspection_only",
        "notes": "v0.1.43 exposes scheduler/resource planning and queue inspection metadata; command execution is not yet routed through this queue.",
        "generated_at_epoch_seconds": time.time(),
    }


def queue_list(repo_path: str | Path = ".") -> dict[str, Any]:
    status = queue_status(repo_path)
    operation_log = Path(status["operation_log"])
    operations: list[dict[str, Any]] = []
    if operation_log.exists():
        for line in operation_log.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                operations.append(item)
    return {
        "ok": True,
        "action": "queue_list",
        "status": "listed",
        "schema": f"{SCHEDULER_SCHEMA}.operations",
        "schema_version": SCHEDULER_SCHEMA_VERSION,
        "repo_path": status["repo_path"],
        "queue_dir": status["queue_dir"],
        "operation_count": len(operations),
        "operations": operations,
    }
