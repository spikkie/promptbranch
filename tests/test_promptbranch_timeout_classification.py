from __future__ import annotations

import argparse

import httpx

from promptbranch_browser_auth.exceptions import BrowserProfileBusyError
from promptbranch_cli import _service_exception_payload


def test_service_exception_payload_classifies_direct_browser_profile_busy() -> None:
    args = argparse.Namespace(command="src", src_command="list", service_timeout_seconds=300.0)
    exc = BrowserProfileBusyError(
        "browser profile is busy",
        operation_name="list_project_sources",
        active_operation="ask_question",
        waited_seconds=30.0,
        retry_after_seconds=30.0,
        profile_dir="/tmp/profile",
    )

    payload = _service_exception_payload(exc, args)

    assert payload is not None
    assert payload["ok"] is False
    assert payload["action"] == "src_list"
    assert payload["status"] == "browser_profile_busy"
    assert payload["operation"] == "list_project_sources"
    assert payload["active_operation"] == "ask_question"
    assert payload["timeout_layer"] == "browser_profile_lock"


def test_service_exception_payload_classifies_service_read_timeout() -> None:
    args = argparse.Namespace(command="ask", service_timeout_seconds=300.0)
    request = httpx.Request("POST", "http://localhost:8000/v1/ask")
    exc = httpx.ReadTimeout("timed out", request=request)

    payload = _service_exception_payload(exc, args)

    assert payload is not None
    assert payload["ok"] is False
    assert payload["action"] == "ask"
    assert payload["status"] == "service_client_read_timeout"
    assert payload["timeout_layer"] == "service_client"
    assert payload["service_timeout_seconds"] == 300.0


def test_service_exception_payload_preserves_http_browser_profile_busy_detail() -> None:
    args = argparse.Namespace(command="src", src_command="list", service_timeout_seconds=300.0)
    request = httpx.Request("GET", "http://localhost:8000/v1/project-sources")
    response = httpx.Response(
        423,
        request=request,
        json={
            "detail": {
                "ok": False,
                "status": "browser_profile_busy",
                "operation": "list_project_sources",
                "active_operation": "ask_question",
                "timeout_layer": "browser_profile_lock",
            }
        },
    )
    exc = httpx.HTTPStatusError("423 Locked", request=request, response=response)

    payload = _service_exception_payload(exc, args)

    assert payload is not None
    assert payload["action"] == "src_list"
    assert payload["status"] == "browser_profile_busy"
    assert payload["active_operation"] == "ask_question"
    assert payload["http_status_code"] == 423

from promptbranch_cli import _source_add_busy_payload


def test_source_add_busy_payload_is_top_level_operator_result() -> None:
    args = argparse.Namespace(value=None, profile_wait_timeout_seconds=120.0)
    payload = _source_add_busy_payload(
        {
            "ok": False,
            "status": "browser_profile_busy",
            "operation": "add_project_source",
            "active_operation": "ask_question",
            "waited_seconds": 30.0,
            "retry_after_seconds": 30.0,
        },
        source_kind="file",
        file_path="/tmp/demo.zip",
        display_name="demo.zip",
        overwrite_existing=True,
        args=args,
    )

    assert payload["action"] == "source_add"
    assert payload["status"] == "browser_profile_busy"
    assert payload["classification"] == "expected_contention"
    assert payload["project_source_mutated"] is False
    assert payload["persistence_verified"] is False
    assert payload["queue_enabled"] is False
    assert payload["active_operation"] == "ask_question"
    assert "--wait-for-profile" in payload["next_safe_commands"][1]
