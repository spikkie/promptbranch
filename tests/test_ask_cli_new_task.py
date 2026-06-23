from __future__ import annotations

import argparse
import asyncio
import json
from types import SimpleNamespace

from promptbranch_cli import DirectBackend, ServiceBackend, cmd_ask, make_parser
from promptbranch_state import ConversationStateStore


PROJECT_HOME = "https://chatgpt.com/g/g-p-1234567890abcdef1234567890abcdef-demo/project"
OLD_CONVERSATION = "https://chatgpt.com/g/g-p-1234567890abcdef1234567890abcdef-demo/c/old-task"
NEW_CONVERSATION = "https://chatgpt.com/g/g-p-1234567890abcdef1234567890abcdef-demo/c/new-task"


def _store(tmp_path):
    profile_dir = tmp_path / ".pb_profile"
    profile_dir.mkdir()
    store = ConversationStateStore(str(profile_dir))
    store.remember_project(PROJECT_HOME, project_name="demo")
    store.remember(PROJECT_HOME, OLD_CONVERSATION, project_name="demo")
    return store


def _service_backend(fake_client, *, store, project_url=PROJECT_HOME):
    backend = object.__new__(ServiceBackend)
    backend._client = fake_client
    backend._service_timeout_seconds = 30.0
    backend._project_url = project_url
    backend._conversation_state = store
    return backend


def test_ask_parser_accepts_new_task_and_alias() -> None:
    parser = make_parser()

    args = parser.parse_args(["ask", "--new-task", "Just say hello"])
    assert args.command == "ask"
    assert args.new_task is True
    assert args.prompt == "Just say hello"

    alias_args = parser.parse_args(["ask", "--new-conversation", "Run a fresh smoke test"])
    assert alias_args.command == "ask"
    assert alias_args.new_task is True
    assert alias_args.prompt == "Run a fresh smoke test"


def test_ask_help_shows_new_task_and_alias(capsys) -> None:
    parser = make_parser()
    try:
        parser.parse_args(["ask", "--help"])
    except SystemExit as exc:
        assert exc.code == 0
    help_text = capsys.readouterr().out
    assert "--new-task" in help_text
    assert "--new-conversation" in help_text


def test_cmd_ask_rejects_new_task_with_conversation_url(capsys) -> None:
    class Backend:
        async def ask(self, **kwargs):  # pragma: no cover - must not be called
            raise AssertionError("ask must not run for invalid target arguments")

    args = argparse.Namespace(
        prompt="Hello",
        prompt_file=None,
        prompt_file_mode=None,
        prompt_file_attach_threshold_bytes=None,
        file=None,
        attachments=[],
        new_task=True,
        conversation_url=OLD_CONVERSATION,
        protocol=False,
        parse_reply=False,
        print_request_json=False,
        json=False,
        text=False,
        keep_open=False,
        retries=None,
    )

    rc = asyncio.run(cmd_ask(Backend(), args))

    assert rc == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["status"] == "invalid_arguments"
    assert payload["error_type"] == "mutually_exclusive_conversation_target"


def test_service_backend_default_ask_reuses_remembered_conversation(tmp_path) -> None:
    store = _store(tmp_path)
    calls: list[dict] = []

    class FakeClient:
        def ask_result(self, prompt, **kwargs):
            calls.append({"prompt": prompt, **kwargs})
            return {
                "ok": True,
                "answer": "ok",
                "conversation_url": OLD_CONVERSATION,
                "submit_evidence": {"submit_causality_confirmed": True},
            }

    backend = _service_backend(FakeClient(), store=store)

    result = asyncio.run(backend.ask("Hello"))

    assert result["ok"] is True
    assert calls[0]["project_url"] == OLD_CONVERSATION
    assert calls[0]["conversation_url"] is None


def test_service_backend_new_task_bypasses_remembered_conversation_and_updates_state(tmp_path) -> None:
    store = _store(tmp_path)
    calls: list[dict] = []

    class FakeClient:
        def ask_result(self, prompt, **kwargs):
            calls.append({"prompt": prompt, **kwargs})
            return {
                "ok": True,
                "answer": "ok",
                "conversation_url": NEW_CONVERSATION,
                "submit_evidence": {"submit_causality_confirmed": True},
            }

    backend = _service_backend(FakeClient(), store=store)

    result = asyncio.run(backend.ask("Hello", new_task=True))

    assert result["ok"] is True
    assert calls[0]["project_url"] == PROJECT_HOME
    assert calls[0]["conversation_url"] is None
    assert store.snapshot(PROJECT_HOME)["conversation_url"] == NEW_CONVERSATION


def test_service_backend_failed_new_task_does_not_overwrite_previous_conversation(tmp_path) -> None:
    store = _store(tmp_path)

    class FakeClient:
        def ask_result(self, prompt, **kwargs):
            return {
                "ok": False,
                "status": "composer_not_ready_before_fill",
                "error_type": "composer_not_ready_before_fill",
                "conversation_url": NEW_CONVERSATION,
            }

    backend = _service_backend(FakeClient(), store=store)

    result = asyncio.run(backend.ask("Hello", new_task=True))

    assert result["ok"] is False
    assert store.snapshot(PROJECT_HOME)["conversation_url"] == OLD_CONVERSATION


def test_direct_backend_new_task_uses_project_home_not_remembered_conversation(tmp_path) -> None:
    store = _store(tmp_path)
    calls: list[dict] = []

    class FakeService:
        def __init__(self):
            self.settings = SimpleNamespace(project_url=PROJECT_HOME)

        async def ask_question_result(self, **kwargs):
            calls.append({"settings_project_url": self.settings.project_url, **kwargs})
            return {
                "ok": True,
                "answer": "ok",
                "conversation_url": NEW_CONVERSATION,
                "submit_evidence": {"submit_backend_commit_confirmed": True},
            }

    backend = DirectBackend(FakeService(), conversation_state=store, project_url=PROJECT_HOME)

    result = asyncio.run(backend.ask("Hello", new_task=True))

    assert result["ok"] is True
    assert calls[0]["settings_project_url"] == PROJECT_HOME
    assert calls[0]["conversation_url"] is None
    assert store.snapshot(PROJECT_HOME)["conversation_url"] == NEW_CONVERSATION


def test_new_task_requires_project_home_when_state_is_empty(tmp_path) -> None:
    profile_dir = tmp_path / ".pb_profile"
    profile_dir.mkdir()
    store = ConversationStateStore(str(profile_dir))

    class FakeClient:
        def ask_result(self, prompt, **kwargs):  # pragma: no cover - must not be called
            raise AssertionError("ask_result must not run without a project home")

    backend = _service_backend(FakeClient(), store=store, project_url="https://chatgpt.com/")

    result = asyncio.run(backend.ask("Hello", new_task=True))

    assert result["ok"] is False
    assert result["status"] == "project_home_url_missing"
    assert result["error_type"] == "project_home_url_missing"
