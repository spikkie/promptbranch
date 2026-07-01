from __future__ import annotations

import asyncio
import time
from pathlib import Path

from promptbranch_browser_auth.client import (
    ChatGPTBrowserClient,
    _AUTH_READINESS_HELD_SESSIONS,
)
from promptbranch_browser_auth.config import ChatGPTBrowserConfig


def _client(tmp_path: Path, *, project_url: str = "https://chatgpt.com/g/demo/project") -> ChatGPTBrowserClient:
    return ChatGPTBrowserClient(
        ChatGPTBrowserConfig(
            project_url=project_url,
            profile_dir=str(tmp_path / "profile"),
            debug=False,
            browser_channel="chrome",
            use_patchright=True,
        )
    )


def setup_function() -> None:
    _AUTH_READINESS_HELD_SESSIONS.clear()


def teardown_function() -> None:
    _AUTH_READINESS_HELD_SESSIONS.clear()


def test_ask_reuses_compatible_held_auth_ready_session_without_clearing_singletons(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, project_url="https://chatgpt.com/g/demo/c/chat-1")
    now = time.monotonic()
    session_key = f"{client._profile_key}|https://chatgpt.com/|{client.driver_name}|chrome"
    page = object()
    context = object()
    _AUTH_READINESS_HELD_SESSIONS[session_key] = {
        "session_key": session_key,
        "operation_name": "auth_readiness",
        "context": context,
        "page": page,
        "created_at_monotonic": now,
        "expires_at_monotonic": now + 300,
        "ttl_seconds": 300,
        "closed": False,
    }

    cleared: list[str] = []
    asked: dict[str, object] = {}

    async def fake_probe(probe_page):
        assert probe_page is page
        return {
            "challenge_detected": False,
            "composer_visible": True,
            "logged_in": True,
            "auth_visible": True,
            "current_url": "https://chatgpt.com/",
            "title": "ChatGPT",
        }

    async def fake_operation(**kwargs):
        asked.update(kwargs)
        return {
            "ok": True,
            "answer": "PB_ASK_OK",
            "conversation_url": "https://chatgpt.com/g/demo/c/chat-1",
            "ask_phase_timings": {},
        }

    monkeypatch.setattr(client, "_probe_auth_readiness_state", fake_probe)
    monkeypatch.setattr(client, "_ask_question_operation", fake_operation)
    monkeypatch.setattr(client, "_clear_profile_singleton_locks", lambda: cleared.append("called") or [])

    result = asyncio.run(client.ask_question_result(prompt="hello"))

    assert result["ok"] is True
    assert result["answer"] == "PB_ASK_OK"
    assert result["held_session_reused"] is True
    assert result["held_session_match_mode"] == "compatible_profile_driver_channel"
    assert asked["page"] is page
    assert asked["context"] is context
    assert cleared == []


def test_ask_closes_challenged_held_session_and_does_not_launch_second_context(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path)
    now = time.monotonic()
    session_key = client._auth_readiness_session_key()
    closed: list[str] = []
    _AUTH_READINESS_HELD_SESSIONS[session_key] = {
        "session_key": session_key,
        "operation_name": "auth_readiness",
        "context": object(),
        "page": object(),
        "created_at_monotonic": now,
        "expires_at_monotonic": now + 300,
        "ttl_seconds": 300,
        "closed": False,
    }

    async def fake_probe(_page):
        return {
            "challenge_detected": True,
            "composer_visible": False,
            "logged_in": False,
            "current_url": "https://chatgpt.com/?__cf_chl_rt_tk=x",
            "title": "Just a moment...",
        }

    async def fake_close(session, *, reason: str):
        closed.append(reason)
        session["closed"] = True

    async def forbidden_run(*_args, **_kwargs):  # pragma: no cover - must not be called
        raise AssertionError("ask should fail fast instead of launching a competing browser context")

    monkeypatch.setattr(client, "_probe_auth_readiness_state", fake_probe)
    monkeypatch.setattr(client, "_close_auth_readiness_held_session", fake_close)
    monkeypatch.setattr(client, "_run_with_context", forbidden_run)

    result = asyncio.run(client.ask_question_result(prompt="hello"))

    assert result["ok"] is False
    assert result["status"] == "held_auth_ready_session_not_ready"
    assert result["held_session_closed"] is True
    assert result["held_session_status"]["status"] == "auth_challenge_detected"
    assert closed == ["ask_preflight_auth_challenge_detected"]
    assert session_key not in _AUTH_READINESS_HELD_SESSIONS


def test_run_with_context_skips_singleton_cleanup_when_held_session_is_active(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path)
    now = time.monotonic()
    session_key = client._auth_readiness_session_key()
    _AUTH_READINESS_HELD_SESSIONS[session_key] = {
        "session_key": session_key,
        "operation_name": "auth_readiness",
        "context": object(),
        "page": object(),
        "created_at_monotonic": now,
        "expires_at_monotonic": now + 300,
        "ttl_seconds": 300,
        "closed": False,
    }

    cleared: list[str] = []

    async def stop_after_spacing():
        raise RuntimeError("stop before launching browser")

    monkeypatch.setattr(client, "_clear_profile_singleton_locks", lambda: cleared.append("called") or [])
    monkeypatch.setattr(client, "_respect_rate_limit_cooldown", lambda: asyncio.sleep(0))
    monkeypatch.setattr(client, "_respect_context_spacing", stop_after_spacing)

    try:
        asyncio.run(client._run_with_context("probe", lambda **_kwargs: {}))
    except RuntimeError as exc:
        assert str(exc) == "stop before launching browser"

    assert cleared == []


def test_ask_operation_sends_through_held_current_page_without_target_navigation(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, project_url="https://chatgpt.com/g/demo/c/chat-1")
    page = object()
    context = object()
    hydration_calls: list[dict[str, object]] = []

    async def fake_probe(probe_page):
        assert probe_page is page
        return {
            "challenge_detected": False,
            "composer_visible": True,
            "logged_in": True,
            "auth_visible": True,
            "current_url": "https://chatgpt.com/",
            "title": "ChatGPT",
        }

    async def forbidden_ensure_logged_in(*_args, **_kwargs):  # pragma: no cover - must not be called
        raise AssertionError("held auth-ready ask must not run ensure_logged_in/navigation precheck")

    async def forbidden_goto(*_args, **_kwargs):  # pragma: no cover - must not be called
        raise AssertionError("held auth-ready ask must not navigate to the target conversation URL")

    async def fake_hydration(*_args, **kwargs):
        hydration_calls.append(kwargs)
        return {"status": "not_required", "target_url": kwargs.get("target_url")}

    async def stop_at_input_wait(*_args, **_kwargs):
        raise RuntimeError("stop after navigation decision")

    monkeypatch.setattr(client, "_probe_auth_readiness_state", fake_probe)
    monkeypatch.setattr(client, "ensure_logged_in", forbidden_ensure_logged_in)
    monkeypatch.setattr(client, "_goto", forbidden_goto)
    monkeypatch.setattr(client, "_ensure_target_conversation_hydrated", fake_hydration)
    monkeypatch.setattr(client, "_wait_for_chat_input", stop_at_input_wait)

    try:
        asyncio.run(
            client._ask_question_operation(
                context=context,
                page=page,
                prompt="hello",
                file_path=None,
                attachment_paths=None,
                conversation_url="https://chatgpt.com/g/demo/c/chat-1",
                expect_json=False,
                keep_open=False,
                service_timeout_seconds=None,
                prefer_button_submit=False,
                reuse_current_page_if_ready=True,
            )
        )
    except RuntimeError as exc:
        assert str(exc) == "stop after navigation decision"

    assert hydration_calls
    assert hydration_calls[0]["target_url"] == "https://chatgpt.com/"
    evidence = hydration_calls[0]["navigation_evidence"]
    assert evidence["mode"] == "held_auth_ready_current_page"
    assert evidence["skipped"] is True
    assert evidence["requested_target_url"] == "https://chatgpt.com/g/demo/c/chat-1"
