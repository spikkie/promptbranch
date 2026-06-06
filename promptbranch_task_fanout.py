from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Iterable


DEFAULT_TASK_FANOUT_CONCURRENCY = 4
MAX_TASK_FANOUT_CONCURRENCY = 8
TASK_FANOUT_SCHEMA_VERSION = "1.0"

READ_ONLY_TASK_FANOUT_POLICY: dict[str, Any] = {
    "risk": "read_backend_or_browser",
    "read_only": True,
    "preferred_executor": "backend_first_then_local_browser_pool",
    "parallel_policy": "parallel_across_tasks_for_reads_only",
    "same_conversation_writes_serialized": True,
    "mutating_operations_rejected": [
        "ask",
        "task_message_answer",
        "src_add",
        "src_sync",
        "artifact_adopt",
        "release_lifecycle",
    ],
    "notes": (
        "Task fan-out may fetch multiple task transcripts concurrently only for read-only operations. "
        "Any write to a conversation remains serialized by task:{conversation_id}:exclusive."
    ),
}


@dataclass(frozen=True)
class TaskFanoutTarget:
    target: str
    id: str
    title: str
    conversation_url: str
    source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def split_task_fanout_targets(values: Iterable[str] | None) -> list[str]:
    """Split repeated/comma-separated task selectors while preserving order."""
    targets: list[str] = []
    for raw in values or []:
        for part in str(raw or "").split(","):
            value = part.strip()
            if value:
                targets.append(value)
    return targets


def normalize_task_fanout_concurrency(value: int | None, *, target_count: int | None = None) -> int:
    try:
        parsed = DEFAULT_TASK_FANOUT_CONCURRENCY if value is None else int(value)
    except (TypeError, ValueError):
        parsed = DEFAULT_TASK_FANOUT_CONCURRENCY
    parsed = max(1, min(parsed, MAX_TASK_FANOUT_CONCURRENCY))
    if target_count is not None and target_count > 0:
        return max(1, min(parsed, target_count))
    return parsed


def deduplicate_task_targets(targets: Iterable[TaskFanoutTarget]) -> list[TaskFanoutTarget]:
    seen: set[str] = set()
    result: list[TaskFanoutTarget] = []
    for target in targets:
        key = target.id or target.conversation_url or target.target
        if key in seen:
            continue
        seen.add(key)
        result.append(target)
    return result


def task_fanout_policy_payload() -> dict[str, Any]:
    return {
        "schema": "promptbranch.task_fanout.policy",
        "schema_version": TASK_FANOUT_SCHEMA_VERSION,
        "ok": True,
        "status": "ready",
        **READ_ONLY_TASK_FANOUT_POLICY,
    }


def task_fanout_plan_payload(
    *,
    targets: list[TaskFanoutTarget],
    requested_targets: list[str],
    concurrency: int,
    operation: str = "task_show",
    task_list_routing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema": "promptbranch.task_fanout.plan",
        "schema_version": TASK_FANOUT_SCHEMA_VERSION,
        "ok": True,
        "action": "parallel_task_fanout",
        "operation": operation,
        "status": "planned",
        "requested_targets": list(requested_targets),
        "target_count": len(targets),
        "concurrency": normalize_task_fanout_concurrency(concurrency, target_count=len(targets)),
        "targets": [target.to_dict() for target in targets],
        "task_list_routing": dict(task_list_routing or {}),
        "policy": dict(READ_ONLY_TASK_FANOUT_POLICY),
        "resource_policy": {
            "task_reads": [f"task:{target.id or target.conversation_url}:read" for target in targets],
            "same_conversation_write_lock": "task:{conversation_id}:exclusive",
            "write_overlap_allowed": False,
        },
    }


def task_fanout_result_payload(
    *,
    plan: dict[str, Any],
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    failures = [item for item in results if not item.get("ok")]
    payload = dict(plan)
    payload.update(
        {
            "schema": "promptbranch.task_fanout.result",
            "action": "parallel_task_fanout",
            "status": "completed" if not failures else "partial",
            "ok": not failures,
            "result_count": len(results),
            "failure_count": len(failures),
            "results": results,
        }
    )
    return payload


def render_task_fanout_summary(payload: dict[str, Any]) -> str:
    lines = [
        f"status={payload.get('status')}",
        f"operation={payload.get('operation')}",
        f"target_count={payload.get('target_count')}",
        f"concurrency={payload.get('concurrency')}",
        f"read_only={payload.get('policy', {}).get('read_only')}",
        f"same_conversation_writes_serialized={payload.get('policy', {}).get('same_conversation_writes_serialized')}",
    ]
    if payload.get("result_count") is not None:
        lines.append(f"result_count={payload.get('result_count')}")
        lines.append(f"failure_count={payload.get('failure_count')}")
    return "\n".join(lines) + "\n"
