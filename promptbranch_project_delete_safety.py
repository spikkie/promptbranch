from __future__ import annotations

from typing import Any

PROJECT_DELETE_DISABLED_STATUS = "project_delete_disabled"
PROJECT_DELETE_POLICY = "frozen_until_secure_delete_protocol"
PROJECT_DELETE_DISABLED_ERROR = (
    "ChatGPT project deletion is disabled in Promptbranch. "
    "Project deletion is too dangerous for the current automation path and must remain "
    "unavailable until a separately designed secure delete protocol is implemented."
)


def project_delete_disabled_result(
    *,
    project_url: str | None = None,
    project_name: str | None = None,
    blocked_at_layer: str | None = None,
) -> dict[str, Any]:
    """Return the canonical fail-closed project deletion payload.

    The payload is deliberately non-destructive and machine-checkable.  It is
    returned instead of opening a browser context or clicking any ChatGPT UI
    deletion affordance.
    """

    result: dict[str, Any] = {
        "ok": False,
        "action": "remove_project",
        "status": PROJECT_DELETE_DISABLED_STATUS,
        "error_type": PROJECT_DELETE_DISABLED_STATUS,
        "error": PROJECT_DELETE_DISABLED_ERROR,
        "project_url": project_url,
        "project_name": project_name,
        "delete_policy": PROJECT_DELETE_POLICY,
        "destructive_action_executed": False,
        "release_blocking": True,
    }
    if blocked_at_layer:
        result["blocked_at_layer"] = blocked_at_layer
    return result


def is_project_delete_disabled_payload(payload: object) -> bool:
    return isinstance(payload, dict) and payload.get("status") == PROJECT_DELETE_DISABLED_STATUS
