from __future__ import annotations

import asyncio
from pathlib import Path

from promptbranch_browser_auth.client import ChatGPTBrowserClient
from promptbranch_browser_auth.config import ChatGPTBrowserConfig


class DirectConversationClient(ChatGPTBrowserClient):
    def __init__(self, tmp_path: Path) -> None:
        self.ask_calls: list[dict] = []
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
    ensure_idx = source.index("project_result = await self._ensure_project_operation")
    direct_idx = source.index("if direct_conversation_mode:")
    assert direct_idx < ensure_idx
