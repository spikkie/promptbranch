from __future__ import annotations

import asyncio
from pathlib import Path

from promptbranch_browser_auth.client import ChatGPTBrowserClient
from promptbranch_browser_auth.config import ChatGPTBrowserConfig


class DirectConversationClient(ChatGPTBrowserClient):
    def __init__(self, tmp_path: Path) -> None:
        self.ask_calls: list[dict] = []
        self.goto_calls: list[dict] = []
        self.challenge_wait_labels: list[str] = []
        self.fail_fast_stages: list[str] = []
        super().__init__(
            ChatGPTBrowserConfig(
                project_url="https://chatgpt.com/g/g-p-demo/c/warmup",
                profile_dir=str(tmp_path / "profile"),
                debug_artifact_dir=str(tmp_path / "debug"),
            )
        )

    def _log(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        return None

    async def _ensure_project_operation(self, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("trusted conversation mode must not run root project discovery")

    async def _goto(self, page, url: str, *, label: str, respect_history_rate_limit_cooldown: bool = True):  # type: ignore[no-untyped-def]
        self.goto_calls.append({
            "url": url,
            "label": label,
            "respect_history_rate_limit_cooldown": respect_history_rate_limit_cooldown,
        })
        return {
            "mode": "goto_domcontentloaded",
            "skipped": False,
            "to_url": url,
            "final_url": url,
            "respect_history_rate_limit_cooldown": respect_history_rate_limit_cooldown,
        }

    async def _wait_for_challenge_resolution(self, page, *, label: str):  # type: ignore[no-untyped-def]
        self.challenge_wait_labels.append(label)

    async def _raise_fail_fast_challenge_if_configured(self, page, *, stage: str):  # type: ignore[no-untyped-def]
        self.fail_fast_stages.append(stage)

    async def _probe_auth_readiness_state(self, page):  # type: ignore[no-untyped-def]
        return {
            "current_url": "https://chatgpt.com/g/g-p-demo/c/warmup?tab=sources",
            "title": "ChatGPT",
            "challenge_detected": False,
            "auth_visible": True,
            "login_visible": False,
            "signup_visible": False,
            "anonymous_visible": False,
            "composer_visible": True,
            "project_page_visible": False,
            "logged_in": True,
            "session_state_reason": "authenticated_indicator_visible",
        }

    async def _ask_question_operation(self, **kwargs):  # type: ignore[no-untyped-def]
        self.ask_calls.append(dict(kwargs))
        return {
            "ok": True,
            "status": "verified",
            "conversation_url": kwargs["conversation_url"],
            "answer": "ASK_SENTINEL" if len(self.ask_calls) == 2 else "BOOTSTRAP_SENTINEL",
        }


def test_release_live_continuous_trusted_conversation_skips_project_discovery(tmp_path: Path) -> None:
    client = DirectConversationClient(tmp_path)
    warmup_url = "https://chatgpt.com/g/g-p-demo/c/warmup?tab=sources"

    result = asyncio.run(
        client._release_live_bootstrap_and_ask_operation(
            context=object(),
            page=object(),
            project_name="promptbranch3",
            bootstrap_prompt="BOOTSTRAP_SENTINEL",
            ask_prompt="ASK_SENTINEL",
            icon=None,
            color=None,
            memory_mode="project-only",
            warmup_conversation_url=warmup_url,
        )
    )

    assert result["ok"] is True
    assert result["status"] == "verified"
    assert result["trusted_conversation_direct_mode"] is True
    assert result["root_project_discovery_skipped"] is True
    assert result["project_identity_source"] == "warmup_conversation_url"
    assert result["project_url"] == "https://chatgpt.com/g/g-p-demo/project"
    assert result["conversation_url"] == warmup_url
    assert result["project_result"]["status"] == "trusted_conversation_url"
    assert result["project_result"]["project_discovery_skipped"] is True
    assert len(client.goto_calls) == 1
    assert client.goto_calls[0] == {
        "url": warmup_url,
        "label": "release-live-continuous-trusted-conversation",
        "respect_history_rate_limit_cooldown": False,
    }
    assert client.challenge_wait_labels == ["release-live-continuous-trusted-conversation"]
    assert client.fail_fast_stages == ["release-live-continuous-trusted-conversation"]
    assert result["project_result"]["trusted_conversation_ready"] is True
    assert result["project_result"]["trusted_conversation_readiness"]["composer_visible"] is True
    assert result["project_result"]["trusted_conversation_readiness"]["logged_in"] is True
    assert result["project_result"]["trusted_conversation_scope"]["matches"] is True
    assert len(client.ask_calls) == 2
    assert [call["conversation_url"] for call in client.ask_calls] == [warmup_url, warmup_url]
    assert client.ask_calls[0]["reuse_current_page_if_ready"] is True
    assert client.ask_calls[1]["reuse_current_page_if_ready"] is True


def test_release_live_continuous_direct_conversation_static_guard() -> None:
    source = (Path(__file__).resolve().parents[1] / "promptbranch_browser_auth" / "client.py").read_text(encoding="utf-8")
    assert "using trusted project conversation URL directly; skipping root project discovery" in source
    assert "root_project_discovery_skipped" in source
    assert "project_identity_source\": \"warmup_conversation_url" in source
    assert "direct_conversation_mode = bool" in source
    assert "bootstrap_target_url = direct_conversation_url if direct_conversation_mode else project_url" in source
    assert "release-live-continuous-trusted-conversation" in source
    assert "trusted conversation page readiness checked before bootstrap ask" in source
    assert "trusted_conversation_not_ready" in source
    ensure_idx = source.index("project_result = await self._ensure_project_operation")
    direct_idx = source.index("if direct_conversation_mode:")
    assert direct_idx < ensure_idx
