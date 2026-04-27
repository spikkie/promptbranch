from __future__ import annotations

import pytest

from promptbranch_full_integration_test import (
    _normalize_expected_missing_resolve_result,
    _extract_conversation_url_from_ask_result,
    _normalize_expected_skip_result,
    _task_messages_payload,
    _wait_for_task_visible_in_list,
    IntegrationAssertionError,
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
            "--post-ask-delay-seconds",
            "1.5",
            "--task-list-visible-timeout-seconds",
            "2.5",
            "--task-list-visible-poll-min-seconds",
            "0.25",
            "--task-list-visible-poll-max-seconds",
            "3.5",
            "--task-list-visible-max-attempts",
            "3",
            "--allow-recent-state-task-fallback",
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
    assert args.post_ask_delay_seconds == 1.5
    assert args.task_list_visible_timeout_seconds == 2.5
    assert args.task_list_visible_poll_min_seconds == 0.25
    assert args.task_list_visible_poll_max_seconds == 3.5
    assert args.task_list_visible_max_attempts == 3
    assert args.allow_recent_state_task_fallback is True
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




def test_wait_for_task_visible_uses_bounded_lightweight_polling(monkeypatch) -> None:
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr("promptbranch_full_integration_test.asyncio.sleep", fake_sleep)

    class FakeService:
        def __init__(self) -> None:
            self.calls: list[bool] = []

        async def list_project_chats(self, *, keep_open: bool = False, include_history_fallback: bool = True):
            self.calls.append(include_history_fallback)
            if len(self.calls) < 3:
                return {
                    "ok": True,
                    "count": 0,
                    "chats": [],
                    "history_fallback_used": include_history_fallback,
                    "source_counts": {"snorlax": 0, "dom": 0, "history": 0},
                }
            return {
                "ok": True,
                "count": 1,
                "chats": [
                    {
                        "id": "abc123",
                        "title": "Visible task",
                        "conversation_url": "https://chatgpt.com/g/g-p-demo/c/abc123",
                    }
                ],
                "history_fallback_used": include_history_fallback,
                "source_counts": {"snorlax": 1, "dom": 0, "history": 0},
            }

    steps = []
    service = FakeService()

    payload, entries, matched = __import__("asyncio").run(
        _wait_for_task_visible_in_list(
            steps,
            service,
            conversation_url="https://chatgpt.com/g/g-p-demo/c/abc123",
            keep_open=False,
            timeout_seconds=60.0,
            poll_min_seconds=1.0,
            poll_max_seconds=2.0,
            max_attempts=4,
        )
    )

    assert payload["count"] == 1
    assert entries[0]["id"] == "abc123"
    assert matched["title"] == "Visible task"
    assert service.calls == [False, False, False]
    assert sleeps == [1.0, 1.75]
    assert steps[-1].name == "task_message_flow.task_list_visible"
    assert steps[-1].ok is True



def test_wait_for_task_visible_rejects_recent_state_only_by_default(monkeypatch) -> None:
    async def fake_sleep(seconds: float) -> None:
        return None

    monkeypatch.setattr("promptbranch_full_integration_test.asyncio.sleep", fake_sleep)

    class FakeService:
        async def list_project_chats(self, *, keep_open: bool = False, include_history_fallback: bool = True):
            return {
                "ok": True,
                "count": 1,
                "chats": [
                    {
                        "id": "abc123",
                        "title": "Recent task",
                        "conversation_url": "https://chatgpt.com/g/g-p-demo/c/abc123",
                        "source": "recent_state",
                    }
                ],
                "visibility_status": "recent_state_only",
                "source_counts": {"snorlax": 0, "dom": 0, "current_page": 0, "history": 0, "recent_state": 1},
            }

    steps = []
    import asyncio
    import pytest

    with pytest.raises(IntegrationAssertionError):
        asyncio.run(
            _wait_for_task_visible_in_list(
                steps,
                FakeService(),
                conversation_url="https://chatgpt.com/g/g-p-demo/c/abc123",
                keep_open=False,
                timeout_seconds=1.0,
                poll_min_seconds=1.0,
                poll_max_seconds=1.0,
                max_attempts=1,
            )
        )

    assert steps[-1].name == "task_message_flow.task_list_visible"
    assert steps[-1].ok is False
    assert steps[-1].details["attempts"][0]["visibility_status"] == "recent_state_only"


def test_wait_for_task_visible_allows_recent_state_only_when_opted_in(monkeypatch) -> None:
    async def fake_sleep(seconds: float) -> None:
        return None

    monkeypatch.setattr("promptbranch_full_integration_test.asyncio.sleep", fake_sleep)

    class FakeService:
        async def list_project_chats(self, *, keep_open: bool = False, include_history_fallback: bool = True):
            return {
                "ok": True,
                "count": 1,
                "chats": [
                    {
                        "id": "abc123",
                        "title": "Recent task",
                        "conversation_url": "https://chatgpt.com/g/g-p-demo/c/abc123",
                        "source": "recent_state",
                    }
                ],
                "visibility_status": "recent_state_only",
                "source_counts": {"snorlax": 0, "dom": 0, "current_page": 0, "history": 0, "recent_state": 1},
            }

    steps = []
    import asyncio

    payload, entries, matched = asyncio.run(
        _wait_for_task_visible_in_list(
            steps,
            FakeService(),
            conversation_url="https://chatgpt.com/g/g-p-demo/c/abc123",
            keep_open=False,
            timeout_seconds=1.0,
            poll_min_seconds=1.0,
            poll_max_seconds=1.0,
            max_attempts=1,
            allow_recent_state_fallback=True,
        )
    )

    assert matched["source"] == "recent_state"
    assert steps[-1].ok is True
    assert steps[-1].details["visibility_status"] == "recent_state_only"
    assert steps[-1].details["degraded"] is True

def test_extract_conversation_url_from_ask_result_can_build_from_project_and_id() -> None:
    result = {
        "project_url": "https://chatgpt.com/g/g-p-demo/project",
        "conversation_id": "abc123",
    }

    assert _extract_conversation_url_from_ask_result(result) == "https://chatgpt.com/g/g-p-demo/c/abc123"

