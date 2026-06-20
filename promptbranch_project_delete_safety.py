from __future__ import annotations

import re
from typing import Any

PROJECT_DELETE_DISABLED_STATUS = "project_delete_disabled"
PROJECT_DELETE_POLICY = "frozen_until_secure_delete_protocol"
EPHEMERAL_TEST_PROJECT_PREFIX = "itest-promptbranch-"
PROJECT_DELETE_DISABLED_ERROR = (
    "ChatGPT project deletion is disabled in Promptbranch. "
    "Project deletion is too dangerous for the current automation path and must remain "
    "unavailable until a separately designed secure delete protocol is implemented."
)
EPHEMERAL_TEST_CLEANUP_POLICY = "same_run_ephemeral_project_cleanup_only"


def extract_project_id(project_url: str | None) -> str | None:
    text = str(project_url or "")
    match = re.search(r"/(g/g-p-[^/?#]+)", text)
    if match:
        return match.group(1).split("/", 1)[1]
    match = re.search(r"\bg-p-[A-Za-z0-9_-]+", text)
    return match.group(0) if match else None


def is_ephemeral_test_project_name(project_name: str | None) -> bool:
    return str(project_name or "").startswith(EPHEMERAL_TEST_PROJECT_PREFIX)


def validate_ephemeral_test_project_cleanup_request(
    *,
    allow_ephemeral_test_cleanup: bool = False,
    project_url: str | None = None,
    project_name: str | None = None,
    created_project_url: str | None = None,
    created_project_name: str | None = None,
    created_project_id: str | None = None,
) -> dict[str, Any]:
    """Validate the only project-deletion exception allowed by Promptbranch.

    Deletion remains frozen for normal/user projects. The only exception is a
    same-run integration-test project whose name and identity are explicitly
    carried from create/ensure into cleanup. The helper returns a structured
    payload so every layer can block without opening a browser when validation
    fails.
    """

    project_id = extract_project_id(project_url)
    expected_id = str(created_project_id or "").strip() or extract_project_id(created_project_url)
    reasons: list[str] = []

    if not allow_ephemeral_test_cleanup:
        reasons.append("allow_ephemeral_test_cleanup_false")
    if not project_url or not project_id:
        reasons.append("project_url_or_id_missing")
    if not is_ephemeral_test_project_name(project_name):
        reasons.append("project_name_not_ephemeral_test_project")
    if created_project_name and project_name and str(created_project_name) != str(project_name):
        reasons.append("created_project_name_mismatch")
    if not created_project_name:
        reasons.append("created_project_name_missing")
    if not expected_id:
        reasons.append("created_project_id_missing")
    if project_id and expected_id and project_id != expected_id:
        reasons.append("project_id_mismatch")

    ok = not reasons
    return {
        "ok": ok,
        "action": "validate_ephemeral_test_project_cleanup",
        "status": "validated" if ok else "blocked",
        "delete_policy": EPHEMERAL_TEST_CLEANUP_POLICY if ok else PROJECT_DELETE_POLICY,
        "allow_ephemeral_test_cleanup": bool(allow_ephemeral_test_cleanup),
        "project_url": project_url,
        "project_name": project_name,
        "project_id": project_id,
        "created_project_url": created_project_url,
        "created_project_name": created_project_name,
        "created_project_id": expected_id,
        "reasons": reasons,
    }


def project_delete_disabled_result(
    *,
    project_url: str | None = None,
    project_name: str | None = None,
    blocked_at_layer: str | None = None,
    validation: dict[str, Any] | None = None,
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
    if validation is not None:
        result["ephemeral_cleanup_validation"] = validation
    return result


def is_project_delete_disabled_payload(payload: object) -> bool:
    return isinstance(payload, dict) and payload.get("status") == PROJECT_DELETE_DISABLED_STATUS
