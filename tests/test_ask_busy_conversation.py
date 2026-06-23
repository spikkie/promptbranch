from __future__ import annotations

import asyncio
from pathlib import Path

from promptbranch_browser_auth.client import ChatGPTBrowserClient
from promptbranch_browser_auth.config import ChatGPTBrowserConfig


PROJECT_HOME = "https://chatgpt.com/g/g-p-1234567890abcdef1234567890abcdef-demo/project"
CONVERSATION_URL = "https://chatgpt.com/g/g-p-1234567890abcdef1234567890abcdef-demo/c/busy-task"


def _make_client(tmp_path: Path) -> ChatGPTBrowserClient:
    profile_dir = tmp_path / "profile"
    profile_dir.mkdir()
    config = ChatGPTBrowserConfig(
        email="user@example.com",
        password="secret",
        project_url=PROJECT_HOME,
        profile_dir=str(profile_dir),
        headless=True,
    )
    return ChatGPTBrowserClient(config)


def test_busy_remembered_conversation_is_classified_without_fill_or_submit(tmp_path) -> None:
    client = _make_client(tmp_path)
    fill_called = False

    async def fake_ensure_logged_in(page, context):
        return None

    async def fake_goto(page, url, label=None):
        return {"mode": "navigate", "url": url}

    async def fake_hydrated(page, *, target_url, label, navigation_evidence=None):
        return {"status": "hydrated"}

    async def fake_wait_for_chat_input(page):
        return object()

    async def fake_wait_for_rate_limit_modal_to_clear(page, label):
        return None

    async def fake_composer_ready(page):
        return {
            "ok": False,
            "status": "composer_not_ready_before_fill",
            "blockers": ["stop_button_visible", "thinking_visible"],
            "send_ready": False,
            "stop_visible": True,
        }

    async def fake_fill(*args, **kwargs):  # pragma: no cover - must not be called
        nonlocal fill_called
        fill_called = True
        return {}

    client.ensure_logged_in = fake_ensure_logged_in
    client._goto = fake_goto
    client._ensure_target_conversation_hydrated = fake_hydrated
    client._wait_for_chat_input = fake_wait_for_chat_input
    client._wait_for_rate_limit_modal_to_clear = fake_wait_for_rate_limit_modal_to_clear
    client._wait_for_composer_ready_before_fill = fake_composer_ready
    client._fill_chat_prompt = fake_fill

    result = asyncio.run(
        client._ask_question_operation(
            context=object(),
            page=object(),
            prompt="Hello",
            file_path=None,
            attachment_paths=None,
            conversation_url=CONVERSATION_URL,
            expect_json=False,
            keep_open=False,
        )
    )

    assert fill_called is False
    assert result["ok"] is False
    assert result["status"] == "target_conversation_busy"
    assert result["error_type"] == "target_conversation_busy"
    assert result["recovery_hint"] == "Wait for the current conversation to finish, stop it manually, or rerun with --new-task."
    assert result["composer_ready_evidence"]["blockers"] == ["stop_button_visible", "thinking_visible"]
