from __future__ import annotations

import asyncio
import hashlib
from typing import Any

import pytest
from pathlib import Path

from promptbranch_full_integration_test import (
    DockerServiceAdapter,
    SOURCE_MUTATION_SERVICE_TIMEOUT_SECONDS,
    StepResult,
    _attach_project_source_failure_diagnostic,
    _normalize_expected_missing_resolve_result,
    _extract_conversation_url_from_ask_result,
    _normalize_expected_skip_result,
    _task_messages_payload,
    _wait_for_task_visible_in_list,
    IntegrationAssertionError,
    make_parser,
    resolve_step_selection,
    run_integration,
    _write_changed_file_source_replacement,
)


def test_parser_accepts_browser_fail_fast() -> None:
    args = make_parser().parse_args(["--fail-fast"])
    assert args.fail_fast is True


def test_run_integration_normalises_expected_missing_before_progress_and_continues(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"resolve": 0, "ensure": 0}
    events: list[dict[str, Any]] = []

    class FakeService:
        async def resolve_project(self, *, name: str, keep_open: bool = False, project_url: str | None = None) -> dict[str, Any]:
            calls["resolve"] += 1
            return {"ok": False, "error": "project_not_found", "match_count": 0}

        async def ensure_project(self, **kwargs: Any) -> dict[str, Any]:
            calls["ensure"] += 1
            return {
                "ok": True,
                "created": True,
                "project_url": "https://chatgpt.com/g/g-p-abc123/project",
            }

    service = FakeService()
    monkeypatch.setattr("promptbranch_full_integration_test.build_service", lambda *args, **kwargs: service)
    args = make_parser().parse_args([
        "--only",
        "project_resolve_before_create,project_ensure_create_or_reuse",
        "--project-name",
        "itest-normalised-missing",
        "--keep-project",
        "--fail-fast",
        "--step-delay-seconds",
        "0",
    ])
    setattr(args, "_progress_callback", lambda **event: events.append(dict(event)))

    result = asyncio.run(run_integration(args))

    assert result["ok"] is True
    assert calls == {"resolve": 1, "ensure": 1}
    assert result["steps"][0]["name"] == "project_resolve_before_create"
    assert result["steps"][0]["ok"] is True
    assert result["steps"][0]["details"]["status"] == "expected_missing"
    resolve_finished = [event for event in events if event["event"] == "finished" and event["step_name"] == "project_resolve_before_create"]
    assert resolve_finished == [{
        "event": "finished",
        "step_name": "project_resolve_before_create",
        "ok": True,
        "duration_seconds": resolve_finished[0]["duration_seconds"],
    }]


def test_run_integration_fail_fast_stops_before_next_browser_step(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"resolve": 0, "ensure": 0}

    class FakeService:
        async def resolve_project(self, *, name: str, keep_open: bool = False, project_url: str | None = None) -> dict[str, Any]:
            calls["resolve"] += 1
            return {"ok": False, "error": "backend_unavailable", "match_count": None}

        async def ensure_project(self, **kwargs: Any) -> dict[str, Any]:
            calls["ensure"] += 1
            raise AssertionError("next browser step must not run after a genuine fail-fast failure")

    service = FakeService()
    monkeypatch.setattr("promptbranch_full_integration_test.build_service", lambda *args, **kwargs: service)
    args = make_parser().parse_args([
        "--only",
        "project_resolve_before_create,project_ensure_create_or_reuse",
        "--project-name",
        "itest-real-failure",
        "--keep-project",
        "--fail-fast",
        "--step-delay-seconds",
        "0",
    ])

    result = asyncio.run(run_integration(args))

    assert result["ok"] is False
    assert result["status"] == "failed_fast"
    assert result["fail_fast_triggered"] is True
    assert result["fail_fast_step"] == "project_resolve_before_create"
    assert calls == {"resolve": 1, "ensure": 0}
    assert [step["name"] for step in result["steps"]] == ["project_resolve_before_create"]
    assert result["steps"][0]["ok"] is False


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


def test_docker_service_adapter_source_mutation_timeout_exceeds_general_client_timeout() -> None:
    adapter = DockerServiceAdapter(
        base_url="http://localhost:8000",
        token=None,
        timeout_seconds=300.0,
        project_url="https://chatgpt.com/g/g-p-123/project",
    )

    assert adapter._source_mutation_timeout_seconds() >= SOURCE_MUTATION_SERVICE_TIMEOUT_SECONDS
    assert adapter._source_mutation_timeout_seconds() > adapter.timeout_seconds




def test_docker_service_adapter_passes_extended_timeout_to_source_add(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class FakeClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            captured["client_timeout"] = kwargs.get("timeout")

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
            return None

        def add_project_source(self, **kwargs: Any) -> dict[str, Any]:
            captured["add_kwargs"] = kwargs
            return {"ok": True}

    monkeypatch.setattr("promptbranch_full_integration_test.ChatGPTServiceClient", FakeClient)

    adapter = DockerServiceAdapter(
        base_url="http://localhost:8000",
        token=None,
        timeout_seconds=300.0,
        project_url="https://chatgpt.com/g/g-p-123/project",
    )

    result = adapter._add_project_source_sync(
        "text",
        "hello",
        None,
        "integration-note",
        True,
        True,
    )

    assert result == {"ok": True}
    assert captured["client_timeout"] == 300.0
    assert captured["add_kwargs"]["request_timeout_seconds"] == adapter._source_mutation_timeout_seconds()
    assert captured["add_kwargs"]["request_timeout_seconds"] > captured["client_timeout"]



def test_docker_service_adapter_source_add_timeout_returns_structured_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    class ReadTimeout(Exception):
        pass

    class FakeClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
            return None

        def add_project_source(self, **kwargs: Any) -> dict[str, Any]:
            raise ReadTimeout("timed out")

    monkeypatch.setattr("promptbranch_full_integration_test.ChatGPTServiceClient", FakeClient)

    adapter = DockerServiceAdapter(
        base_url="http://localhost:8000",
        token=None,
        timeout_seconds=300.0,
        project_url="https://chatgpt.com/g/g-p-123/project",
    )

    result = adapter._add_project_source_sync(
        "text",
        "hello",
        None,
        "integration-note",
        True,
        True,
    )

    assert result["ok"] is False
    assert result["status"] == "source_mutation_request_timeout"
    assert result["release_blocking"] is True
    assert result["request_timeout_seconds"] == adapter._source_mutation_timeout_seconds()
    assert result["request_timeout_seconds"] > result["general_service_timeout_seconds"]
    assert result["recovery_guidance"]


def test_source_add_timeout_failure_diagnostic_lists_sources() -> None:
    class FakeProjectService:
        async def list_project_sources(self, *, keep_open: bool = False) -> dict[str, Any]:
            assert keep_open is True
            return {"ok": True, "action": "list", "sources": [{"name": "maybe-late-source"}]}

    steps: list[StepResult] = []
    failure_payload: dict[str, Any] = {
        "ok": False,
        "status": "source_mutation_request_timeout",
        "error_type": "ReadTimeout",
    }

    asyncio.run(
        _attach_project_source_failure_diagnostic(
            steps,
            FakeProjectService(),
            failure_payload,
            diagnostic_step_name="project_source_list_after_add_text_failure",
            keep_open=True,
        )
    )

    assert failure_payload["post_failure_source_list_command"] == "pb src list --json"
    assert failure_payload["post_failure_source_list_diagnostic"]["ok"] is True
    assert steps[-1].name == "project_source_list_after_add_text_failure"
    assert steps[-1].ok is True

def test_post_commit_source_failure_diagnostic_lists_retained_project_sources() -> None:
    class FakeProjectService:
        async def list_project_sources(self, *, keep_open: bool = False) -> dict[str, Any]:
            assert keep_open is True
            return {
                "ok": True,
                "action": "list",
                "sources": [{"name": "late-visible-source.txt"}],
            }

    steps: list[StepResult] = []
    failure_payload: dict[str, Any] = {
        "ok": False,
        "status": "post_commit_source_surface_not_refreshed",
        "transaction_status": "commit_seen_with_stale_inflight_not_verified_present",
    }

    asyncio.run(
        _attach_project_source_failure_diagnostic(
            steps,
            FakeProjectService(),
            failure_payload,
            diagnostic_step_name="project_source_list_after_add_text_failure",
            keep_open=True,
        )
    )

    assert failure_payload["post_failure_source_list_command"] == "pb src list --json"
    diagnostic = failure_payload["post_failure_source_list_diagnostic"]
    assert diagnostic["ok"] is True
    assert diagnostic["source_list"]["sources"][0]["name"] == "late-visible-source.txt"
    assert steps[-1].name == "project_source_list_after_add_text_failure"
    assert steps[-1].ok is True



def test_resolve_step_selection_expands_aliases_and_forces_login_and_capabilities() -> None:
    selection = resolve_step_selection(
        only_values=["source_add_text,ask"],
        skip_values=[],
        keep_project=False,
    )
    assert selection.requested_only == ("source_add_text", "ask")
    assert selection.enabled_steps == (
        "project_source_capabilities",
        "project_source_add_text",
        "ask_question",
    )




def test_resolve_step_selection_supports_source_overwrite_file_alias() -> None:
    selection = resolve_step_selection(
        only_values=["source_overwrite_file"],
        skip_values=[],
        keep_project=False,
    )
    assert selection.enabled_steps == (
        "project_source_capabilities",
        "project_source_overwrite_file",
    )


def test_resolve_step_selection_source_add_includes_overwrite_regression() -> None:
    selection = resolve_step_selection(
        only_values=["source_add"],
        skip_values=[],
        keep_project=False,
    )
    assert "project_source_add_file" in selection.enabled_steps
    assert "project_source_overwrite_file" in selection.enabled_steps

def test_resolve_step_selection_skips_cleanup_when_keep_project_enabled() -> None:
    selection = resolve_step_selection(
        only_values=[],
        skip_values=[],
        keep_project=True,
    )
    assert "project_remove_cleanup" not in selection.enabled_steps
    assert "mcp_smoke" in selection.enabled_steps
    assert "login_check" not in selection.enabled_steps


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
    assert selection.enabled_steps == ("project_list_debug",)


def test_resolve_step_selection_keeps_explicit_login_diagnostic() -> None:
    selection = resolve_step_selection(
        only_values=["login"],
        skip_values=[],
        keep_project=False,
    )
    assert selection.enabled_steps == ("login_check",)


def test_resolve_step_selection_supports_mcp_smoke_without_login() -> None:
    selection = resolve_step_selection(
        only_values=["mcp"],
        skip_values=[],
        keep_project=False,
    )
    assert selection.enabled_steps == ("mcp_smoke",)


def test_resolve_step_selection_supports_mcp_host_smoke_without_login() -> None:
    selection = resolve_step_selection(
        only_values=["mcp_host_smoke"],
        skip_values=[],
        keep_project=False,
    )
    assert selection.enabled_steps == ("mcp_host_smoke",)


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
    assert selection.enabled_steps == ("task_message_flow",)


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



def test_project_remove_cleanup_is_non_destructive_even_when_service_is_dangerous(monkeypatch) -> None:
    import asyncio
    from promptbranch_full_integration_test import _remove_project_cleanup_with_retry

    async def fake_sleep(seconds: float) -> None:
        raise AssertionError("cleanup should not wait/retry because deletion is frozen before service calls")

    monkeypatch.setattr("promptbranch_full_integration_test.asyncio.sleep", fake_sleep)

    class DangerousService:
        project_url = "https://chatgpt.com/g/g-p-danger-itest-promptbranch-run/project"

        def __init__(self) -> None:
            self.remove_called = False
            self.resolve_called = False

        async def remove_project(self, **_kwargs):  # pragma: no cover - should not be reached
            self.remove_called = True
            return {"ok": True, "status": "removed"}

        async def resolve_project(self, **_kwargs):  # pragma: no cover - should not be reached
            self.resolve_called = True
            return {"ok": True, "match_count": 1}

    service = DangerousService()
    cleanup_steps = []
    result = asyncio.run(
        _remove_project_cleanup_with_retry(
            cleanup_steps,
            service,
            keep_open=False,
            step_delay_seconds=0.0,
            max_attempts=3,
            project_name="itest-promptbranch-run",
            allow_ephemeral_test_cleanup=True,
            created_project_url=service.project_url,
            created_project_name="itest-promptbranch-run",
            created_project_id="g-p-danger",
        )
    )

    assert service.remove_called is False
    assert service.resolve_called is False
    assert result["ok"] is True
    assert result["status"] == "project_remove_cleanup_skipped_delete_frozen"
    assert result["postcondition"] == "temporary_project_retained_delete_frozen"
    assert result["cleanup_policy"] == "no_project_delete_until_secure_protocol"
    assert result["destructive_action_executed"] is False
    assert result["allow_ephemeral_test_cleanup_requested"] is True
    assert cleanup_steps[-1].ok is True
    assert cleanup_steps[-1].details == result


def test_project_remove_cleanup_does_not_retarget_or_verify_absence_when_delete_is_frozen() -> None:
    import asyncio
    from promptbranch_full_integration_test import _remove_project_cleanup_with_retry

    class ServiceWithProjectUrl:
        project_url = "https://chatgpt.com/g/g-p-base/project"

        async def remove_project(self, **_kwargs):  # pragma: no cover - should not be reached
            raise AssertionError("remove_project must not be called")

        async def resolve_project(self, **_kwargs):  # pragma: no cover - should not be reached
            raise AssertionError("resolve_project must not be called")

    cleanup_steps = []
    result = asyncio.run(
        _remove_project_cleanup_with_retry(
            cleanup_steps,
            ServiceWithProjectUrl(),
            keep_open=False,
            step_delay_seconds=0.0,
            max_attempts=2,
            project_name="itest-leak",
        )
    )

    assert result["status"] == "project_remove_cleanup_skipped_delete_frozen"
    assert result["postcondition"] == "temporary_project_retained_delete_frozen"
    assert result["cleanup_policy"] == "no_project_delete_until_secure_protocol"
    assert result["project_url"] == "https://chatgpt.com/g/g-p-base/project"
    assert "absence_verification" not in result
    assert cleanup_steps == cleanup_steps[:1]


def test_run_step_marks_returned_false_result_as_failed() -> None:
    import asyncio
    import promptbranch_full_integration_test as integration

    async def returns_false_result():
        return {"ok": False, "status": "persistence_not_verified"}

    steps = []
    result = asyncio.run(integration._run_step(steps, "project_source_add_file", returns_false_result()))

    assert result["ok"] is False
    assert len(steps) == 1
    assert steps[0].name == "project_source_add_file"
    assert steps[0].ok is False
    assert steps[0].details["status"] == "persistence_not_verified"


def test_resolve_step_selection_adds_cleanup_for_focused_create_flow() -> None:
    selection = resolve_step_selection(
        only_values=["project_ensure", "source_add_text"],
        skip_values=[],
        keep_project=False,
    )
    assert "project_remove_cleanup" in selection.enabled_steps


def test_resolve_step_selection_keeps_existing_project_source_only_without_cleanup() -> None:
    selection = resolve_step_selection(
        only_values=["source_add_text"],
        skip_values=[],
        keep_project=False,
    )
    assert "project_remove_cleanup" not in selection.enabled_steps


def test_project_remove_cleanup_retains_project_without_calling_service_remove(monkeypatch) -> None:
    import asyncio
    from promptbranch_full_integration_test import _remove_project_cleanup_with_retry

    async def fake_sleep(seconds: float) -> None:
        return None

    monkeypatch.setattr("promptbranch_full_integration_test.asyncio.sleep", fake_sleep)

    class FakeService:
        project_url = "https://chatgpt.com/g/g-p-demo-itest-promptbranch-run/project"

        def __init__(self) -> None:
            self.remove_called = False

        async def remove_project(self, **kwargs):  # pragma: no cover - should not be reached
            self.remove_called = True
            raise AssertionError("cleanup must not call remove_project")

    service = FakeService()
    cleanup_steps = []
    result = asyncio.run(
        _remove_project_cleanup_with_retry(
            cleanup_steps,
            service,
            keep_open=False,
            step_delay_seconds=0.0,
            max_attempts=1,
            project_name="itest-promptbranch-run",
            allow_ephemeral_test_cleanup=True,
            created_project_url="https://chatgpt.com/g/g-p-demo-itest-promptbranch-run/project",
            created_project_name="itest-promptbranch-run",
            created_project_id="g-p-demo-itest-promptbranch-run",
        )
    )

    assert service.remove_called is False
    assert result["ok"] is True
    assert result["status"] == "project_remove_cleanup_skipped_delete_frozen"
    assert result["postcondition"] == "temporary_project_retained_delete_frozen"
    assert result["cleanup_policy"] == "no_project_delete_until_secure_protocol"
    assert result["destructive_action_executed"] is False
    assert result["allow_ephemeral_test_cleanup_requested"] is True
    assert cleanup_steps[-1].ok is True


def test_full_integration_cleanup_evidence_has_no_stale_ephemeral_policy_label() -> None:
    source = Path("promptbranch_full_integration_test.py").read_text(encoding="utf-8")
    stale_policy = "_".join(["same", "run", "ephemeral", "cleanup"])
    assert stale_policy not in source
    assert "no_project_delete_until_secure_protocol" in source


def test_changed_content_overwrite_fixture_changes_sha256(tmp_path: Path) -> None:
    path = tmp_path / "source.txt"
    initial_content = "generation=initial\n"
    path.write_text(initial_content, encoding="utf-8")
    initial_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()

    replacement_sha256 = _write_changed_file_source_replacement(
        path,
        run_id="unit-run",
        initial_file_content=initial_content,
        initial_file_sha256=initial_sha256,
    )

    assert replacement_sha256 != initial_sha256
    assert replacement_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert "proof=changed-content-indexed-family-overwrite" in path.read_text(encoding="utf-8")
