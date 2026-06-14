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


PARALLEL_ASK_RELEASE_INTENT_KINDS = {
    "software_release_request",
    "software_release_candidate_request",
}


def _normalize_version_for_compare(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return text[1:] if text.lower().startswith("v") else text


def parallel_ask_is_release_like(
    *,
    intent_kind: str | None,
    target_version: str | None = None,
    baseline_artifact: str | None = None,
    baseline_version: str | None = None,
    release_type: str | None = None,
) -> bool:
    """Return whether a parallel ask plan would carry release/baseline authority."""

    normalized_intent = str(intent_kind or "").strip()
    return (
        normalized_intent in PARALLEL_ASK_RELEASE_INTENT_KINDS
        or bool(str(target_version or "").strip())
        or bool(str(baseline_artifact or "").strip())
        or bool(str(baseline_version or "").strip())
        or str(release_type or "normal").strip() == "repair"
    )




def _artifact_current_sections(artifact_current: dict[str, Any] | None) -> dict[str, Any]:
    """Return selected artifact-current sections using repo-loop payloads first.

    This module is intentionally standalone to avoid importing the CLI. Legacy
    top-level payloads remain a compatibility fallback for older callers/tests.
    """

    payload = artifact_current if isinstance(artifact_current, dict) else {}
    repos = payload.get("repos") if isinstance(payload.get("repos"), dict) else {}
    selected = None
    if repos:
        for key in sorted(repos):
            repo_payload = repos.get(key)
            if isinstance(repo_payload, dict):
                selected = repo_payload
                break
    if selected is None:
        selected = payload
    runtime = selected.get("runtime") if isinstance(selected.get("runtime"), dict) else {}
    consistency = selected.get("consistency") if isinstance(selected.get("consistency"), dict) else {}
    return {"runtime": runtime, "consistency": consistency}


def parallel_ask_baseline_safety(
    *,
    request: dict[str, Any],
    artifact_current: dict[str, Any] | None,
    release_like: bool,
) -> dict[str, Any]:
    """Classify whether a protocol ask plan may safely carry artifact baseline data."""

    artifact = request.get("artifact") if isinstance(request.get("artifact"), dict) else {}
    sections = _artifact_current_sections(artifact_current)
    runtime = sections["runtime"]
    consistency = sections["consistency"]
    runtime_version = runtime.get("version")
    protocol_baseline_version = artifact.get("current_version")
    baseline_override = bool(artifact.get("baseline_override"))
    runtime_norm = _normalize_version_for_compare(runtime_version)
    baseline_norm = _normalize_version_for_compare(protocol_baseline_version)
    versions_match = bool(runtime_norm and baseline_norm and runtime_norm == baseline_norm)
    stale = bool(runtime_norm and baseline_norm and not versions_match)

    status = "fresh"
    ok = True
    blocking = False
    if baseline_override:
        status = "explicit_baseline_override"
    elif stale and release_like:
        ok = False
        blocking = True
        status = "stale_release_baseline_blocked"
    elif stale:
        status = "stale_non_release_baseline_allowed"

    return {
        "ok": ok,
        "status": status,
        "blocking": blocking,
        "release_like": bool(release_like),
        "baseline_override": baseline_override,
        "runtime_version": runtime_version,
        "protocol_baseline_version": protocol_baseline_version,
        "protocol_baseline_artifact": artifact.get("current_baseline"),
        "versions_match": versions_match,
        "code_version_matches_state_source": consistency.get("code_version_matches_state_source"),
        "state_source_matches_state_artifact": consistency.get("state_source_matches_state_artifact"),
        "operator_instruction": (
            "Refusing to emit release-style parallel ask envelopes from a stale artifact baseline; "
            "run pb artifact current --json / adopt-current, or pass explicit --baseline-artifact/--baseline-version after verifying baseline continuity."
            if blocking
            else "Parallel ask plan is planning-only; no prompts were sent."
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
    baseline_safety: dict[str, Any] | None = None,
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
        "baseline_safety": dict(baseline_safety or {}),
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
