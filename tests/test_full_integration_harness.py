from __future__ import annotations

import pytest

from promptbranch_full_integration_test import (
    _normalize_expected_missing_resolve_result,
    _extract_conversation_url_from_ask_result,
    _normalize_expected_skip_result,
    _task_messages_payload,
    make_parser,
    resolve_step_selection,
)


def test_parser_accepts_skip_only_keep_project_and_strict_remove_ui() -> None:
    parser = make_parser()
    args = parser.parse_args(
        [
            "--only",
            "source_add_text,ask",
            "--skip",
            "project_remove",
            "--keep-project",
            "--strict-remove-ui",
            "--step-delay-seconds",
            "0.25",
            "--service-base-url",
            "http://localhost:8000",
            "--service-token",
            "secret-token",
            "--service-timeout-seconds",
            "45",
        ]
    )
    assert args.only == ["source_add_text,ask"]
    assert args.skip == ["project_remove"]
    assert args.keep_project is True
    assert args.strict_remove_ui is True
    assert args.step_delay_seconds == 0.25
    assert args.service_base_url == "http://localhost:8000"
    assert args.service_token == "secret-token"
    assert args.service_timeout_seconds == 45.0


def test_resolve_step_selection_expands_aliases_and_forces_login_and_capabilities() -> None:
    selection = resolve_step_selection(
        only_values=["source_add_text,ask"],
        skip_values=[],
        keep_project=False,
    )
    assert selection.requested_only == ("source_add_text", "ask")
    assert selection.enabled_steps == (
        "login_check",
        "project_source_capabilities",
        "project_source_add_text",
        "ask_question",
    )


def test_resolve_step_selection_skips_cleanup_when_keep_project_enabled() -> None:
    selection = resolve_step_selection(
        only_values=[],
        skip_values=[],
        keep_project=True,
    )
    assert "project_remove_cleanup" not in selection.enabled_steps
    assert "login_check" in selection.enabled_steps


@pytest.mark.parametrize("token", ["does-not-exist", "source_add_text,unknown"])
def test_resolve_step_selection_rejects_unknown_steps(token: str) -> None:
    with pytest.raises(ValueError):
        resolve_step_selection(only_values=[token], skip_values=[], keep_project=False)


def test_resolve_step_selection_raises_when_all_steps_removed() -> None:
    with pytest.raises(ValueError):
        resolve_step_selection(only_values=["login"], skip_values=["login"], keep_project=False)


def test_resolve_step_selection_supports_project_list_debug() -> None:
    selection = resolve_step_selection(
        only_values=["project_list_debug"],
        skip_values=[],
        keep_project=False,
    )
    assert selection.enabled_steps == (
        "login_check",
        "project_list_debug",
    )


def test_parser_accepts_project_list_debug_options() -> None:
    parser = make_parser()
    args = parser.parse_args(
        [
            "--only",
            "project_list_debug",
            "--project-list-debug-scroll-rounds",
            "9",
            "--project-list-debug-wait-ms",
            "500",
            "--project-list-debug-manual-pause",
        ]
    )
    assert args.only == ["project_list_debug"]
    assert args.project_list_debug_scroll_rounds == 9
    assert args.project_list_debug_wait_ms == 500
    assert args.project_list_debug_manual_pause is True


def test_normalize_expected_missing_resolve_result_marks_project_not_found_as_expected() -> None:
    result = {"ok": False, "error": "project_not_found", "match_count": 0}
    normalized = _normalize_expected_missing_resolve_result(result)
    assert normalized["ok"] is True
    assert normalized["service_ok"] is False
    assert normalized["expected_missing"] is True
    assert normalized["status"] == "expected_missing"


def test_normalize_expected_missing_resolve_result_leaves_other_results_unchanged() -> None:
    result = {"ok": True, "match_count": 1}
    normalized = _normalize_expected_missing_resolve_result(result)
    assert normalized == result


def test_normalize_expected_skip_result_marks_unsupported_as_expected() -> None:
    result = {"skipped": True, "reason": "unsupported", "requested_source_kind": "link"}
    normalized = _normalize_expected_skip_result(result)
    assert normalized["ok"] is True
    assert normalized["service_ok"] is None
    assert normalized["expected_unsupported"] is True
    assert normalized["status"] == "expected_unsupported"


def test_normalize_expected_skip_result_marks_generic_skip_as_expected() -> None:
    result = {"skipped": True, "reason": "precondition"}
    normalized = _normalize_expected_skip_result(result)
    assert normalized["ok"] is True
    assert normalized["expected_skip"] is True
    assert normalized["status"] == "expected_skip"


def test_normalize_expected_skip_result_leaves_non_skip_results_unchanged() -> None:
    result = {"ok": True, "reason": "supported"}
    normalized = _normalize_expected_skip_result(result)
    assert normalized == result

def test_resolve_step_selection_supports_task_message_flow_aliases() -> None:
    selection = resolve_step_selection(
        only_values=["task_messages"],
        skip_values=[],
        keep_project=False,
    )
    assert selection.enabled_steps == (
        "login_check",
        "task_message_flow",
    )


def test_task_messages_payload_groups_mapping_payload() -> None:
    payload = {
        "ok": True,
        "conversation_url": "https://chatgpt.com/g/g-p-demo/c/abc",
        "conversation_id": "abc",
        "title": "Smoke task",
        "current_node": "assistant-1",
        "mapping": {
            "root": {"parent": None, "message": None},
            "user-1": {
                "parent": "root",
                "message": {
                    "author": {"role": "user"},
                    "content": {"parts": ["Promptbranch smoke question"]},
                },
            },
            "assistant-1": {
                "parent": "user-1",
                "message": {
                    "author": {"role": "assistant"},
                    "content": {"parts": ["TASK_MESSAGE_OK"]},
                },
            },
        },
    }

    grouped = _task_messages_payload(payload)

    assert grouped["message_count"] == 1
    assert grouped["messages"][0]["text"] == "Promptbranch smoke question"
    assert grouped["messages"][0]["answer_count"] == 1
    assert grouped["messages"][0]["answers"][0]["text"] == "TASK_MESSAGE_OK"


def test_extract_conversation_url_from_ask_result_can_build_from_project_and_id() -> None:
    result = {
        "project_url": "https://chatgpt.com/g/g-p-demo/project",
        "conversation_id": "abc123",
    }

    assert _extract_conversation_url_from_ask_result(result) == "https://chatgpt.com/g/g-p-demo/c/abc123"

