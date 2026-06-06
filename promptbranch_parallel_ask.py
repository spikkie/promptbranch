from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from promptbranch_ask_protocol import REQUEST_SCHEMA, REQUEST_SCHEMA_VERSION
from promptbranch_task_fanout import TaskFanoutTarget

DEFAULT_PARALLEL_ASK_CONCURRENCY = 2
MAX_PARALLEL_ASK_CONCURRENCY = 4
PARALLEL_ASK_SCHEMA_VERSION = "1.0"

PROTOCOL_BOUND_PARALLEL_ASK_POLICY: dict[str, Any] = {
    "risk": "write_conversation",
    "planning_only": True,
    "automation_performed": False,
    "protocol_required": True,
    "protocol_schema": REQUEST_SCHEMA,
    "protocol_schema_version": REQUEST_SCHEMA_VERSION,
    "parallel_policy": "parallel_across_distinct_conversations_only",
    "same_conversation_writes_serialized": True,
    "same_conversation_write_lock": "task:{conversation_id}:exclusive",
    "profile_slot_required_before_execution": True,
    "queue_required_before_execution": True,
    "notes": (
        "This planner may group protocol asks for different conversations into the same parallel batch, "
        "but repeated asks targeting the same conversation stay in that conversation's serial group. "
        "It does not send prompts; execution remains blocked until a later scheduler/executor slice."
    ),
}


@dataclass(frozen=True)
class ParallelAskRequestPlan:
    target: TaskFanoutTarget
    request_id: str
    correlation_id: str
    request: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target.to_dict(),
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "request": self.request,
            "conversation_lock": conversation_write_lock(self.target),
        }


def normalize_parallel_ask_concurrency(value: int | None, *, group_count: int | None = None) -> int:
    try:
        parsed = DEFAULT_PARALLEL_ASK_CONCURRENCY if value is None else int(value)
    except (TypeError, ValueError):
        parsed = DEFAULT_PARALLEL_ASK_CONCURRENCY
    parsed = max(1, min(parsed, MAX_PARALLEL_ASK_CONCURRENCY))
    if group_count is not None and group_count > 0:
        return max(1, min(parsed, group_count))
    return parsed


def conversation_key(target: TaskFanoutTarget) -> str:
    return str(target.id or target.conversation_url or target.target).strip() or "unknown"


def conversation_write_lock(target: TaskFanoutTarget) -> str:
    return f"task:{conversation_key(target)}:exclusive"


def build_parallel_ask_serial_groups(requests: Iterable[ParallelAskRequestPlan]) -> list[dict[str, Any]]:
    grouped: "OrderedDict[str, list[ParallelAskRequestPlan]]" = OrderedDict()
    for request in requests:
        grouped.setdefault(conversation_key(request.target), []).append(request)
    groups: list[dict[str, Any]] = []
    for key, items in grouped.items():
        groups.append(
            {
                "conversation_key": key,
                "conversation_url": items[0].target.conversation_url,
                "conversation_lock": conversation_write_lock(items[0].target),
                "request_count": len(items),
                "parallel_eligible": len(items) == 1,
                "serialization_required": len(items) > 1,
                "request_ids": [item.request_id for item in items],
                "targets": [item.target.to_dict() for item in items],
            }
        )
    return groups


def parallel_ask_policy_payload() -> dict[str, Any]:
    return {
        "schema": "promptbranch.parallel_ask.policy",
        "schema_version": PARALLEL_ASK_SCHEMA_VERSION,
        "ok": True,
        "status": "ready",
        **PROTOCOL_BOUND_PARALLEL_ASK_POLICY,
    }


def parallel_ask_plan_payload(
    *,
    requests: list[ParallelAskRequestPlan],
    requested_targets: list[str],
    concurrency: int,
    prompt: str,
    task_list_routing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    serial_groups = build_parallel_ask_serial_groups(requests)
    serialized_groups = [group for group in serial_groups if group["serialization_required"]]
    effective_concurrency = normalize_parallel_ask_concurrency(concurrency, group_count=len(serial_groups))
    return {
        "schema": "promptbranch.parallel_ask.plan",
        "schema_version": PARALLEL_ASK_SCHEMA_VERSION,
        "ok": True,
        "action": "parallel_ask_plan",
        "status": "planned",
        "automation_performed": False,
        "planning_only": True,
        "requested_targets": list(requested_targets),
        "target_count": len(requests),
        "request_count": len(requests),
        "conversation_group_count": len(serial_groups),
        "serialized_group_count": len(serialized_groups),
        "concurrency": effective_concurrency,
        "prompt_preview": prompt[:160],
        "prompt_length": len(prompt),
        "task_list_routing": dict(task_list_routing or {}),
        "policy": dict(PROTOCOL_BOUND_PARALLEL_ASK_POLICY),
        "resource_policy": {
            "conversation_write_locks": [group["conversation_lock"] for group in serial_groups],
            "parallel_execution_unit": "conversation_serial_group",
            "same_conversation_write_lock": "task:{conversation_id}:exclusive",
            "same_conversation_overlap_allowed": False,
            "different_conversation_parallel_allowed": True,
            "profile_slots_required": min(effective_concurrency, len(serial_groups)),
        },
        "serial_groups": serial_groups,
        "protocol_requests": [request.to_dict() for request in requests],
    }


def render_parallel_ask_summary(payload: dict[str, Any]) -> str:
    lines = [
        f"status={payload.get('status')}",
        f"action={payload.get('action')}",
        f"target_count={payload.get('target_count')}",
        f"conversation_group_count={payload.get('conversation_group_count')}",
        f"serialized_group_count={payload.get('serialized_group_count')}",
        f"concurrency={payload.get('concurrency')}",
        f"protocol_required={payload.get('policy', {}).get('protocol_required')}",
        f"same_conversation_writes_serialized={payload.get('policy', {}).get('same_conversation_writes_serialized')}",
        f"automation_performed={payload.get('automation_performed')}",
    ]
    return "\n".join(lines) + "\n"
