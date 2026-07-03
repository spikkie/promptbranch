from __future__ import annotations

from typing import Any

BACKEND_TASK_SOURCES = ("snorlax", "project_endpoint", "history", "history_detail")
FALLBACK_TASK_SOURCES = ("dom", "current_page", "recent_state", "current_state")
SOURCE_BACKEND_SIGNALS = ("backend", "project_endpoint", "snorlax", "api", "network")



BACKEND_DIAGNOSTIC_STATUS_VALUES = (
    "ok",
    "rate_limited",
    "forbidden",
    "unauthenticated",
    "backend_schema_changed",
    "backend_unavailable",
)

BACKEND_DIAGNOSTIC_ENDPOINTS: dict[str, dict[str, Any]] = {
    "projects": {
        "scope": "projects",
        "operation": "project_backend_probe",
        "method": "GET",
        "endpoint_family": "snorlax_sidebar",
        "known_paths": ["/backend-api/gizmos/snorlax/sidebar"],
        "mutation_allowed": False,
        "expected_shape": "project/sidebar payload with project records or visible project list metadata",
    },
    "conversations": {
        "scope": "conversations",
        "operation": "conversation_backend_probe",
        "method": "GET",
        "endpoint_family": "project_conversations_or_history",
        "known_paths": [
            "/backend-api/gizmos/{project_id}/conversations",
            "/backend-api/conversations",
            "/backend-api/conversation/{conversation_id}",
        ],
        "mutation_allowed": False,
        "expected_shape": "project-scoped conversation records, history records, or detail metadata",
    },
}


def _textish(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _extract_http_status(payload: Any) -> int | None:
    data = _as_mapping(payload)
    for key in ("http_status", "status_code", "response_status"):
        value = data.get(key)
        try:
            if value is not None:
                return int(value)
        except (TypeError, ValueError):
            pass
    response = data.get("response")
    if isinstance(response, dict):
        for key in ("status", "status_code"):
            try:
                if response.get(key) is not None:
                    return int(response.get(key))
            except (TypeError, ValueError):
                pass
    return None


def _extract_retry_after(payload: Any) -> str | int | float | None:
    data = _as_mapping(payload)
    for key in ("retry_after", "retry_after_seconds", "retry-after"):
        if data.get(key) is not None:
            return data.get(key)
    headers = data.get("headers")
    if isinstance(headers, dict):
        for key, value in headers.items():
            if str(key).casefold() == "retry-after":
                return value
    return None


def _shape_summary(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        keys = sorted(str(key) for key in payload.keys())[:40]
        summary: dict[str, Any] = {
            "type": "object",
            "key_count": len(payload),
            "keys": keys,
        }
        for list_key in ("items", "projects", "conversations", "sources", "records", "data"):
            value = payload.get(list_key)
            if isinstance(value, list):
                summary[f"{list_key}_count"] = len(value)
        return summary
    if isinstance(payload, list):
        return {"type": "array", "count": len(payload)}
    if payload is None:
        return {"type": "null"}
    return {"type": type(payload).__name__}


def classify_backend_diagnostic_payload(payload: Any) -> dict[str, Any]:
    """Classify a raw read-only ChatGPT backend probe result.

    This deliberately avoids trusting the backend schema.  It records the HTTP
    status, retry-after signal, modal/rate-limit hints, and only a shallow shape
    summary so diagnostics remain safe to publish in logs.
    """

    data = _as_mapping(payload)
    http_status = _extract_http_status(data)
    retry_after = _extract_retry_after(data)
    text = " ".join(
        _textish(data.get(key))
        for key in ("status", "error", "message", "modal_text", "body_text")
    ).casefold()
    modal = data.get("modal") if isinstance(data.get("modal"), dict) else {}
    modal_text = _textish(modal.get("text") or modal.get("message")).casefold()
    combined = f"{text} {modal_text}"

    if http_status == 429 or retry_after is not None or "too many requests" in combined or "rate limit" in combined or "rate_limited" in combined:
        status = "rate_limited"
    elif http_status == 401 or "unauthenticated" in combined or "login" in combined and "required" in combined:
        status = "unauthenticated"
    elif http_status == 403 or "forbidden" in combined or "access denied" in combined:
        status = "forbidden"
    elif http_status is not None and http_status >= 500:
        status = "backend_unavailable"
    elif data.get("ok") is False and http_status is None:
        status = "backend_unavailable"
    elif data.get("schema_changed") or data.get("metadata_gap"):
        status = "backend_schema_changed"
    else:
        shape = _shape_summary(data)
        has_known_content = any(
            str(key).endswith("_count") and isinstance(value, int) and value > 0
            for key, value in shape.items()
        ) or bool(data.get("ok", True))
        status = "ok" if has_known_content else "backend_schema_changed"

    return {
        "ok": status == "ok",
        "status": status,
        "http_status": http_status,
        "retry_after": retry_after,
        "rate_limit_detected": status == "rate_limited",
        "modal_detected": bool(modal.get("detected")),
        "response_shape": _shape_summary(data),
    }


def backend_debug_plan(scope: str = "all") -> dict[str, Any]:
    if scope not in {"all", "projects", "conversations"}:
        return {
            "ok": False,
            "action": "debug_backend",
            "schema": "promptbranch.backend.diagnostic",
            "schema_version": "1.0",
            "status": "unknown_scope",
            "scope": scope,
            "known_scopes": ["all", "projects", "conversations"],
        }
    selected = BACKEND_DIAGNOSTIC_ENDPOINTS if scope == "all" else {scope: BACKEND_DIAGNOSTIC_ENDPOINTS[scope]}
    return {
        "ok": True,
        "action": "debug_backend",
        "schema": "promptbranch.backend.diagnostic",
        "schema_version": "1.0",
        "status": "planned",
        "scope": scope,
        "runtime_integration": "read_only_backend_diagnostic",
        "mutation_allowed": False,
        "status_values": list(BACKEND_DIAGNOSTIC_STATUS_VALUES),
        "endpoints": selected,
    }


def backend_debug_diagnostics(*, scope: str = "all", projects_payload: Any | None = None, conversations_payload: Any | None = None) -> dict[str, Any]:
    result = backend_debug_plan(scope)
    if not result.get("ok"):
        return result
    diagnostics: dict[str, Any] = {}
    if scope in {"all", "projects"} and projects_payload is not None:
        item = classify_backend_diagnostic_payload(projects_payload)
        item.update({"scope": "projects", "endpoint_family": BACKEND_DIAGNOSTIC_ENDPOINTS["projects"]["endpoint_family"]})
        diagnostics["projects"] = item
    if scope in {"all", "conversations"} and conversations_payload is not None:
        item = classify_backend_diagnostic_payload(conversations_payload)
        item.update({"scope": "conversations", "endpoint_family": BACKEND_DIAGNOSTIC_ENDPOINTS["conversations"]["endpoint_family"]})
        diagnostics["conversations"] = item
    statuses = [item.get("status") for item in diagnostics.values() if isinstance(item, dict)]
    priority = ["rate_limited", "unauthenticated", "forbidden", "backend_unavailable", "backend_schema_changed"]
    status = "diagnosed" if diagnostics else "planned"
    for candidate in priority:
        if candidate in statuses:
            status = candidate
            break
    if diagnostics and status == "diagnosed" and all(value == "ok" for value in statuses):
        status = "ok"
    result.update({
        "status": status,
        "ok": status in {"planned", "diagnosed", "ok"},
        "diagnostics": diagnostics,
        "diagnostic_count": len(diagnostics),
    })
    return result


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
