from __future__ import annotations

from pathlib import Path

from chatgpt_browser_auth.client import ChatGPTBrowserClient
from chatgpt_browser_auth.config import ChatGPTBrowserConfig


def _make_client(tmp_path: Path) -> ChatGPTBrowserClient:
    config = ChatGPTBrowserConfig(
        project_url="https://chatgpt.com/",
        profile_dir=str(tmp_path / "profile"),
        debug=False,
        save_trace=False,
        save_html=False,
        save_screenshot=False,
    )
    return ChatGPTBrowserClient(config)


def test_response_completion_ready_after_observed_run_then_idle(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    assert client._response_completion_signal_ready(
        current_url="https://chatgpt.com/c/abc123",
        content_present=True,
        stop_visible=False,
        thinking_visible=False,
        observed_running_state=True,
        observed_idle_after_running=True,
    ) is True


def test_response_completion_ready_uses_idle_text_fallback_on_conversation_url(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    assert client._response_completion_signal_ready(
        current_url="https://chatgpt.com/g/g-p-1234567890abcdef/project/c/abc123".replace("/project/c/", "/c/"),
        content_present=True,
        stop_visible=False,
        thinking_visible=False,
        observed_running_state=False,
        observed_idle_after_running=False,
    ) is True


def test_response_completion_ready_does_not_fire_on_project_home_without_run_signal(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    assert client._response_completion_signal_ready(
        current_url="https://chatgpt.com/g/g-p-1234567890abcdef/project",
        content_present=True,
        stop_visible=False,
        thinking_visible=False,
        observed_running_state=False,
        observed_idle_after_running=False,
    ) is False


def test_response_completion_ready_does_not_fire_while_thinking_or_stop_visible(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    assert client._response_completion_signal_ready(
        current_url="https://chatgpt.com/c/abc123",
        content_present=True,
        stop_visible=True,
        thinking_visible=False,
        observed_running_state=False,
        observed_idle_after_running=False,
    ) is False
    assert client._response_completion_signal_ready(
        current_url="https://chatgpt.com/c/abc123",
        content_present=True,
        stop_visible=False,
        thinking_visible=True,
        observed_running_state=False,
        observed_idle_after_running=False,
    ) is False
