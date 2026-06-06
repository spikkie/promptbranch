from __future__ import annotations

from typing import Any

BACKEND_TASK_SOURCES = ("snorlax", "project_endpoint", "history", "history_detail")
FALLBACK_TASK_SOURCES = ("dom", "current_page", "recent_state", "current_state")
SOURCE_BACKEND_SIGNALS = ("backend", "project_endpoint", "snorlax", "api", "network")

READ_OPERATION_PLANS: dict[str, dict[str, Any]] = {
    "task_list": {
        "operation": "task_list",
        "command": "pb task list --json",
        "scope": "task",
        "risk": "read",
        "mutation_allowed": False,
        "source_of_truth_order": [
            "backend JSON / network payload",
            "Promptbranch state cache",
            "DOM scraping fallback",
            "OCR/image fallback blocked for automation",
        ],
        "backend_preferred_sources": list(BACKEND_TASK_SOURCES),
        "fallback_sources": list(FALLBACK_TASK_SOURCES),
        "diagnostic_payload_fields": [
            "source_counts",
            "visibility_status",
            "indexed_task_count",
            "indexed_observation_count",
            "recent_state_count",
        ],
    },
    "source_list": {
        "operation": "source_list",
        "command": "pb src list --json",
        "scope": "project_sources",
        "risk": "read",
        "mutation_allowed": False,
        "source_of_truth_order": [
            "backend JSON / network payload",
            "Promptbranch state cache",
            "DOM scraping fallback",
            "OCR/image fallback blocked for automation",
        ],
        "backend_preferred_sources": list(SOURCE_BACKEND_SIGNALS),
        "fallback_sources": ["dom", "ui", "unknown"],
        "diagnostic_payload_fields": [
            "source_origin",
            "source_counts",
            "sources",
            "count",
            "metadata_gap",
        ],
    },
}


def _as_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _intish(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _counts_for(payload: dict[str, Any]) -> dict[str, int]:
    raw = payload.get("source_counts")
    if not isinstance(raw, dict):
        return {}
    return {str(key): _intish(value) for key, value in raw.items()}


def classify_task_list_payload(payload: Any) -> dict[str, Any]:
    data = _as_mapping(payload)
    counts = _counts_for(data)
    backend_count = sum(counts.get(name, 0) for name in BACKEND_TASK_SOURCES)
    fallback_count = sum(counts.get(name, 0) for name in FALLBACK_TASK_SOURCES)
    indexed_count = _intish(data.get("indexed_task_count"))
    recent_state_count = _intish(data.get("recent_state_count"))
    count = _intish(data.get("count"))

    if backend_count > 0 or indexed_count > 0:
        status = "backend_indexed"
    elif fallback_count > 0:
        status = "fallback_only"
    elif recent_state_count > 0:
        status = "recent_state_only"
    elif count > 0:
        status = "undifferentiated"
    else:
        status = "missing"

    return {
        "operation": "task_list",
        "status": status,
        "ok": status not in {"missing"},
        "backend_observation_count": backend_count,
        "fallback_observation_count": fallback_count,
        "indexed_task_count": indexed_count,
        "recent_state_count": recent_state_count,
        "count": count,
        "source_counts": counts,
        "backend_first_satisfied": status == "backend_indexed",
        "fallback_used": fallback_count > 0,
        "metadata_gap": False,
    }


def _source_origin_from_payload(data: dict[str, Any]) -> str | None:
    for key in ("source_origin", "source_of_truth", "read_source", "source"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def classify_source_list_payload(payload: Any) -> dict[str, Any]:
    data = _as_mapping(payload)
    counts = _counts_for(data)
    origin = _source_origin_from_payload(data)
    sources = [item for item in _as_list(data.get("sources")) if isinstance(item, dict)]
    count = _intish(data.get("count")) or len(sources)
    origin_text = (origin or "").casefold()
    backend_count = sum(counts.get(name, 0) for name in SOURCE_BACKEND_SIGNALS)
    dom_count = counts.get("dom", 0) + counts.get("ui", 0)

    if backend_count > 0 or any(signal in origin_text for signal in SOURCE_BACKEND_SIGNALS):
        status = "backend_indexed"
        metadata_gap = False
    elif dom_count > 0 or "dom" in origin_text or "ui" in origin_text:
        status = "fallback_only"
        metadata_gap = False
    elif count > 0:
        status = "undifferentiated"
        metadata_gap = True
    else:
        status = "missing"
        metadata_gap = not bool(origin or counts)

    return {
        "operation": "source_list",
        "status": status,
        "ok": status not in {"missing"},
        "backend_observation_count": backend_count,
        "fallback_observation_count": dom_count,
        "count": count,
        "source_origin": origin,
        "source_counts": counts,
        "backend_first_satisfied": status == "backend_indexed",
        "fallback_used": status == "fallback_only",
        "metadata_gap": metadata_gap,
    }


def backend_reads_plan(operation: str | None = None) -> dict[str, Any]:
    if operation and operation != "all":
        plan = READ_OPERATION_PLANS.get(operation)
        if plan is None:
            return {
                "ok": False,
                "action": "debug_backend_reads",
                "status": "unknown_operation",
                "operation": operation,
                "known_operations": sorted(READ_OPERATION_PLANS),
            }
        operations = {operation: plan}
    else:
        operations = dict(READ_OPERATION_PLANS)
    return {
        "ok": True,
        "action": "debug_backend_reads",
        "schema": "promptbranch.backend_reads.plan",
        "schema_version": "1.0",
        "status": "planned",
        "operation": operation or "all",
        "runtime_integration": "read_only_diagnostic",
        "operations": operations,
        "decision_rule": "backend_observation_count > 0 should be preferred; DOM/current-state rows are fallbacks and must be explicit in diagnostics.",
    }


def backend_reads_diagnostics(
    *,
    task_payload: Any | None = None,
    source_payload: Any | None = None,
    operation: str | None = None,
) -> dict[str, Any]:
    selected = operation or "all"
    plan = backend_reads_plan(selected)
    if not plan.get("ok"):
        return plan

    diagnostics: dict[str, Any] = {}
    if selected in {"all", "task_list"} and task_payload is not None:
        diagnostics["task_list"] = classify_task_list_payload(task_payload)
    if selected in {"all", "source_list"} and source_payload is not None:
        diagnostics["source_list"] = classify_source_list_payload(source_payload)

    metadata_gaps = [
        name for name, item in diagnostics.items()
        if isinstance(item, dict) and item.get("metadata_gap")
    ]
    backend_first_missing = [
        name for name, item in diagnostics.items()
        if isinstance(item, dict) and item.get("ok") and not item.get("backend_first_satisfied")
    ]

    status = "diagnosed" if diagnostics else "planned"
    if metadata_gaps:
        status = "metadata_gap"
    elif backend_first_missing:
        status = "fallback_visible"

    result = dict(plan)
    result.update({
        "status": status,
        "diagnostics": diagnostics,
        "diagnostic_count": len(diagnostics),
        "metadata_gaps": metadata_gaps,
        "backend_first_missing": backend_first_missing,
    })
    return result


def task_list_read_routing(payload: Any, *, history_fallback_requested: bool = False, history_fallback_used: bool = False) -> dict[str, Any]:
    """Return the runtime read-routing decision for `pb task list`.

    v0.1.46 starts routing task reads from the same backend-read evidence
    exposed by `pb debug backend-reads`. Backend-indexed observations win;
    global history/DOM/current-state rows are explicit fallbacks rather than an
    invisible blend.
    """

    diagnostic = classify_task_list_payload(payload)
    backend_first = bool(diagnostic.get("backend_first_satisfied"))
    if backend_first:
        selected_path = "backend_first"
        fallback_policy = "skip_history_fallback_when_backend_indexed"
    elif history_fallback_used:
        selected_path = "history_fallback"
        fallback_policy = "used_after_backend_missing"
    elif diagnostic.get("status") == "fallback_only":
        selected_path = "indexed_fallback"
        fallback_policy = "fallback_visible"
    elif diagnostic.get("status") == "recent_state_only":
        selected_path = "state_fallback"
        fallback_policy = "recent_state_only"
    else:
        selected_path = "missing"
        fallback_policy = "no_read_path_verified"

    return {
        "operation": "task_list",
        "mode": "backend_first",
        "selected_path": selected_path,
        "status": diagnostic.get("status"),
        "backend_first_satisfied": backend_first,
        "history_fallback_requested": bool(history_fallback_requested),
        "history_fallback_used": bool(history_fallback_used),
        "fallback_policy": fallback_policy,
        "backend_observation_count": diagnostic.get("backend_observation_count", 0),
        "fallback_observation_count": diagnostic.get("fallback_observation_count", 0),
        "metadata_gap": bool(diagnostic.get("metadata_gap")),
    }


def source_list_read_routing(payload: Any) -> dict[str, Any]:
    """Return the runtime read-routing decision for `pb src list`.

    Source listing still lacks reliable backend-vs-DOM provenance in the current
    service payload, so v0.1.46 deliberately exposes the fallback/metadata-gap
    instead of pretending the source path is backend-first.
    """

    diagnostic = classify_source_list_payload(payload)
    backend_first = bool(diagnostic.get("backend_first_satisfied"))
    metadata_gap = bool(diagnostic.get("metadata_gap"))
    if backend_first:
        selected_path = "backend_first"
        fallback_policy = "backend_provenance_available"
    elif metadata_gap:
        selected_path = "explicit_fallback_metadata_gap"
        fallback_policy = "do_not_route_backend_first_until_source_provenance_exists"
    elif diagnostic.get("fallback_used"):
        selected_path = "explicit_fallback"
        fallback_policy = "fallback_visible"
    else:
        selected_path = "missing" if diagnostic.get("status") == "missing" else "undifferentiated"
        fallback_policy = "source_provenance_required"

    return {
        "operation": "source_list",
        "mode": "backend_first_blocked" if metadata_gap else "backend_first",
        "selected_path": selected_path,
        "status": diagnostic.get("status"),
        "backend_first_satisfied": backend_first,
        "fallback_used": bool(diagnostic.get("fallback_used")),
        "fallback_policy": fallback_policy,
        "backend_observation_count": diagnostic.get("backend_observation_count", 0),
        "fallback_observation_count": diagnostic.get("fallback_observation_count", 0),
        "metadata_gap": metadata_gap,
    }
