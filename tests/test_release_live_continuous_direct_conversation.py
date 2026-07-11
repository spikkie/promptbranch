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


def test_release_live_continuous_browser_lifetime_submit_failure_static_guard() -> None:
    source = (Path(__file__).resolve().parents[1] / "promptbranch_browser_auth" / "client.py").read_text(encoding="utf-8")
    assert "browser_context_closed_during_submit" in source
    assert "browser/page context closed during composer submit; returning structured live browser lifetime failure" in source
    assert "composer_wait" in source
    assert "submit_subphase" in source
    assert "browser target closed while waiting for chat input; stopping selector iteration" in source
    assert "pre_composer_click_closed" in source
    assert "composer_click" in source
    assert "prompt_fill" in source
    assert "submit_dispatch" in source
    assert "challenge_evidence_present" in source


def test_wait_for_chat_input_target_closed_is_not_response_timeout_static_guard() -> None:
    source = (Path(__file__).resolve().parents[1] / "promptbranch_browser_auth" / "client.py").read_text(encoding="utf-8")
    target_closed_log_idx = source.index("browser target closed while waiting for chat input; stopping selector iteration")
    response_timeout_idx = source.index('raise ResponseTimeoutError("Chat input did not become visible")')
    assert target_closed_log_idx < response_timeout_idx
    assert 'return await browser_lifetime_failure_result(submit_phase="composer_wait", exc=exc)' in source


def test_click_fallback_short_circuits_target_closed_static_guard() -> None:
    source = (Path(__file__).resolve().parents[1] / "promptbranch_browser_auth" / "client.py").read_text(encoding="utf-8")
    assert "_is_browser_target_closed_error" in source
    assert "browser target closed during primary click; skipping click fallbacks" in source
    assert "browser target closed during force click; skipping remaining click fallbacks" in source
    assert "browser target closed during mouse coordinate click; skipping remaining click fallbacks" in source
    assert "browser target closed during evaluate click" in source


class CompletedSentinelClient(DirectConversationClient):
    async def _ask_question_operation(self, **kwargs):  # type: ignore[no-untyped-def]
        self.ask_calls.append(dict(kwargs))
        return {
            "status": "completed",
            "conversation_url": kwargs["conversation_url"],
            "answer": "ASK_SENTINEL" if len(self.ask_calls) == 2 else "BOOTSTRAP_SENTINEL",
        }


def test_release_live_continuous_completed_sentinel_results_are_ok_without_subresult_ok(tmp_path: Path) -> None:
    client = CompletedSentinelClient(tmp_path)
    warmup_url = "https://chatgpt.com/g/g-p-demo/c/warmup?tab=sources"

    result = asyncio.run(
        client._release_live_bootstrap_and_ask_operation(
            context=object(),
            page=object(),
            project_name="promptbranch3",
            bootstrap_prompt="Reply with exactly the single token BOOTSTRAP_SENTINEL and nothing else.",
            ask_prompt="Return exactly the single token ASK_SENTINEL and nothing else.",
            icon=None,
            color=None,
            memory_mode="project-only",
            warmup_conversation_url=warmup_url,
        )
    )

    assert result["ok"] is True
    assert result["status"] == "completed"
    assert "failed_phase" not in result
    assert result["contains_expected_sentinel"] is True
    assert result["bootstrap_completed_with_expected_sentinel"] is True
    assert result["ask_completed_with_expected_sentinel"] is True
    assert result["bootstrap_result"]["status"] == "completed"
    assert result["ask_result"]["status"] == "completed"
    assert result["ask_result"]["answer"] == "ASK_SENTINEL"


def test_release_live_continuous_completed_sentinel_success_static_guard() -> None:
    source = (Path(__file__).resolve().parents[1] / "promptbranch_browser_auth" / "client.py").read_text(encoding="utf-8")
    assert "_release_live_result_completed_with_expected_token" in source
    assert "sentinel_completed_ok" in source
    assert 'status = "completed"' in source
    assert '"contains_expected_sentinel": ask_completed_with_expected_token' in source
    assert 'if not ok:\n            result["failed_phase"] = (' in source
    assert 'else "ask_live"' in source


class BootstrapGuardrailRetryClient(DirectConversationClient):
    @staticmethod
    def _release_live_guardrail_cooldown_seconds() -> float:
        return 0.0

    async def _ask_question_operation(self, **kwargs):  # type: ignore[no-untyped-def]
        self.ask_calls.append(dict(kwargs))
        if len(self.ask_calls) == 1:
            self._record_rate_limit_event(
                kind="backend_api_guardrail",
                trigger="release_live_bootstrap",
                status=429,
                url=kwargs["conversation_url"],
            )
            return {
                "status": "completed",
                "conversation_url": kwargs["conversation_url"],
                "answer": "BOOTSTRAP_SENTINEL",
            }
        return {
            "status": "completed",
            "conversation_url": kwargs["conversation_url"],
            "answer": "ASK_SENTINEL" if len(self.ask_calls) == 3 else "BOOTSTRAP_SENTINEL",
        }


def test_release_live_continuous_retries_bootstrap_once_after_guardrail_when_readiness_clean(tmp_path: Path) -> None:
    client = BootstrapGuardrailRetryClient(tmp_path)
    warmup_url = "https://chatgpt.com/g/g-p-demo/c/warmup?tab=sources"

    result = asyncio.run(
        client._release_live_bootstrap_and_ask_operation(
            context=object(),
            page=object(),
            project_name="promptbranch3",
            bootstrap_prompt="Reply with exactly the single token BOOTSTRAP_SENTINEL and nothing else.",
            ask_prompt="Return exactly the single token ASK_SENTINEL and nothing else.",
            icon=None,
            color=None,
            memory_mode="project-only",
            warmup_conversation_url=warmup_url,
        )
    )

    assert result["ok"] is True
    assert result["status"] == "completed"
    assert result["bootstrap_guardrail_retry"]["ok"] is True
    assert result["bootstrap_guardrail_retry"]["retry_attempted"] is True
    assert result["bootstrap_guardrail_retry"]["retry_guardrail_persisted"] is not True if "retry_guardrail_persisted" in result["bootstrap_guardrail_retry"] else True
    assert len(client.ask_calls) == 3
    assert [call["conversation_url"] for call in client.ask_calls] == [warmup_url, warmup_url, warmup_url]
    assert result["bootstrap_result"]["answer"] == "BOOTSTRAP_SENTINEL"
    assert result["ask_result"]["answer"] == "ASK_SENTINEL"


def test_release_live_continuous_guardrail_retry_static_guard() -> None:
    source = (Path(__file__).resolve().parents[1] / "promptbranch_browser_auth" / "client.py").read_text(encoding="utf-8")
    assert "PROMPTBRANCH_RELEASE_LIVE_BOOTSTRAP_GUARDRAIL_COOLDOWN_SECONDS" in source
    assert "release_live_bootstrap_guardrail_cooldown_wait" in source
    assert "retry_limit" in source
    assert "retry_limit=1" in source
    assert "ready_for_single_bootstrap_retry" in source
    assert "bootstrap_guardrail_retry" in source
    assert "retry_guardrail_persisted" in source
    assert "bypass=False" in source or "\"bypass\": False" in source


class BootstrapSentinelMissingRetrySuccessClient(DirectConversationClient):
    async def _ask_question_operation(self, **kwargs):  # type: ignore[no-untyped-def]
        self.ask_calls.append(dict(kwargs))
        if len(self.ask_calls) == 1:
            return {
                "status": "completed",
                "conversation_url": kwargs["conversation_url"],
                "answer": "WRONG_BOOTSTRAP_SENTINEL",
            }
        if len(self.ask_calls) == 2:
            return {
                "status": "completed",
                "conversation_url": kwargs["conversation_url"],
                "answer": "ASK_SENTINEL",
            }
        return {
            "status": "completed",
            "conversation_url": kwargs["conversation_url"],
            "answer": "BOOTSTRAP_SENTINEL",
        }


class BootstrapSentinelMissingRetryFailureClient(DirectConversationClient):
    async def _ask_question_operation(self, **kwargs):  # type: ignore[no-untyped-def]
        self.ask_calls.append(dict(kwargs))
        if len(self.ask_calls) == 2:
            return {
                "status": "completed",
                "conversation_url": kwargs["conversation_url"],
                "answer": "ASK_SENTINEL",
            }
        return {
            "status": "completed",
            "conversation_url": kwargs["conversation_url"],
            "answer": "WRONG_BOOTSTRAP_SENTINEL",
        }


def test_release_live_continuous_retries_missing_bootstrap_sentinel_once_after_ask_success(tmp_path: Path) -> None:
    client = BootstrapSentinelMissingRetrySuccessClient(tmp_path)
    warmup_url = "https://chatgpt.com/g/g-p-demo/c/warmup?tab=sources"

    result = asyncio.run(
        client._release_live_bootstrap_and_ask_operation(
            context=object(),
            page=object(),
            project_name="promptbranch3",
            bootstrap_prompt="Reply with exactly the single token BOOTSTRAP_SENTINEL and nothing else.",
            ask_prompt="Return exactly the single token ASK_SENTINEL and nothing else.",
            icon=None,
            color=None,
            memory_mode="project-only",
            warmup_conversation_url=warmup_url,
        )
    )

    assert result["ok"] is True
    assert result["status"] == "completed"
    assert result["bootstrap_guardrail_retry"] is None
    assert result["bootstrap_sentinel_retry"]["ok"] is True
    assert result["bootstrap_sentinel_retry"]["retry_attempted"] is True
    assert result["bootstrap_sentinel_retry"]["retry_completed_with_expected_sentinel"] is True
    assert result["bootstrap_completed_with_expected_sentinel"] is True
    assert result["ask_completed_with_expected_sentinel"] is True
    assert len(client.ask_calls) == 3
    assert [call["prompt"] for call in client.ask_calls] == [
        "Reply with exactly the single token BOOTSTRAP_SENTINEL and nothing else.",
        "Return exactly the single token ASK_SENTINEL and nothing else.",
        "Reply with exactly the single token BOOTSTRAP_SENTINEL and nothing else.",
    ]


def test_release_live_continuous_missing_bootstrap_sentinel_after_ask_success_has_precise_status(tmp_path: Path) -> None:
    client = BootstrapSentinelMissingRetryFailureClient(tmp_path)
    warmup_url = "https://chatgpt.com/g/g-p-demo/c/warmup?tab=sources"

    result = asyncio.run(
        client._release_live_bootstrap_and_ask_operation(
            context=object(),
            page=object(),
            project_name="promptbranch3",
            bootstrap_prompt="Reply with exactly the single token BOOTSTRAP_SENTINEL and nothing else.",
            ask_prompt="Return exactly the single token ASK_SENTINEL and nothing else.",
            icon=None,
            color=None,
            memory_mode="project-only",
            warmup_conversation_url=warmup_url,
        )
    )

    assert result["ok"] is False
    assert result["status"] == "bootstrap_sentinel_missing_after_ask_success"
    assert result["failed_phase"] == "live_conversation_bootstrap"
    assert result["bootstrap_guardrail_retry"] is None
    assert result["bootstrap_sentinel_retry"]["retry_attempted"] is True
    assert result["bootstrap_sentinel_retry"]["retry_completed_with_expected_sentinel"] is False
    assert result["bootstrap_completed_with_expected_sentinel"] is False
    assert result["ask_completed_with_expected_sentinel"] is True
    assert len(client.ask_calls) == 3


def test_release_live_continuous_bootstrap_sentinel_missing_static_guard() -> None:
    source = (Path(__file__).resolve().parents[1] / "promptbranch_browser_auth" / "client.py").read_text(encoding="utf-8")
    assert "bootstrap_sentinel_missing_after_ask_success" in source
    assert "_release_live_bootstrap_sentinel_retry_gate" in source
    assert "release_live_bootstrap_sentinel_retry_gate" in source
    assert "if (not bootstrap_completed_with_expected_token) and ask_completed_with_expected_token" in source
    assert "retry_completed_with_expected_sentinel" in source
    assert 'result["failed_phase"] = (' in source

class VisibleThinkingPreambleCompletedSentinelClient(DirectConversationClient):
    async def _ask_question_operation(self, **kwargs):  # type: ignore[no-untyped-def]
        self.ask_calls.append(dict(kwargs))
        return {
            "status": "completed",
            "conversation_url": kwargs["conversation_url"],
            "answer": (
                "Thought for a few seconds\nASK_SENTINEL"
                if len(self.ask_calls) == 2
                else "Thought for a couple of seconds\n\nBOOTSTRAP_SENTINEL"
            ),
        }


class ArbitraryPrefixCompletedSentinelClient(DirectConversationClient):
    async def _ask_question_operation(self, **kwargs):  # type: ignore[no-untyped-def]
        self.ask_calls.append(dict(kwargs))
        if len(self.ask_calls) == 2:
            return {
                "status": "completed",
                "conversation_url": kwargs["conversation_url"],
                "answer": "ASK_SENTINEL",
            }
        return {
            "status": "completed",
            "conversation_url": kwargs["conversation_url"],
            "answer": "Here is the token:\nBOOTSTRAP_SENTINEL",
        }


def test_release_live_accepts_known_visible_thinking_preamble_before_exact_sentinel(tmp_path: Path) -> None:
    client = VisibleThinkingPreambleCompletedSentinelClient(tmp_path)
    warmup_url = "https://chatgpt.com/g/g-p-demo/c/warmup?tab=sources"

    result = asyncio.run(
        client._release_live_bootstrap_and_ask_operation(
            context=object(),
            page=object(),
            project_name="promptbranch3",
            bootstrap_prompt="Reply with exactly the single token BOOTSTRAP_SENTINEL and nothing else.",
            ask_prompt="Return exactly the single token ASK_SENTINEL and nothing else.",
            icon=None,
            color=None,
            memory_mode="project-only",
            warmup_conversation_url=warmup_url,
        )
    )

    assert result["ok"] is True
    assert result["status"] == "completed"
    assert result["bootstrap_sentinel_retry"] is None
    assert result["bootstrap_completed_with_expected_sentinel"] is True
    assert result["ask_completed_with_expected_sentinel"] is True
    assert result["contains_expected_sentinel"] is True
    assert len(client.ask_calls) == 2


def test_release_live_rejects_arbitrary_prefix_before_exact_sentinel(tmp_path: Path) -> None:
    client = ArbitraryPrefixCompletedSentinelClient(tmp_path)
    warmup_url = "https://chatgpt.com/g/g-p-demo/c/warmup?tab=sources"

    result = asyncio.run(
        client._release_live_bootstrap_and_ask_operation(
            context=object(),
            page=object(),
            project_name="promptbranch3",
            bootstrap_prompt="Reply with exactly the single token BOOTSTRAP_SENTINEL and nothing else.",
            ask_prompt="Return exactly the single token ASK_SENTINEL and nothing else.",
            icon=None,
            color=None,
            memory_mode="project-only",
            warmup_conversation_url=warmup_url,
        )
    )

    assert result["ok"] is False
    assert result["status"] == "bootstrap_sentinel_missing_after_ask_success"
    assert result["failed_phase"] == "live_conversation_bootstrap"
    assert result["bootstrap_completed_with_expected_sentinel"] is False
    assert result["ask_completed_with_expected_sentinel"] is True
    assert result["bootstrap_sentinel_retry"]["retry_attempted"] is True
    assert result["bootstrap_sentinel_retry"]["retry_completed_with_expected_sentinel"] is False


def test_release_live_visible_thinking_preamble_normalization_static_guard() -> None:
    source = (Path(__file__).resolve().parents[1] / "promptbranch_browser_auth" / "client.py").read_text(encoding="utf-8")
    assert "_RELEASE_LIVE_VISIBLE_THINKING_PREAMBLES" in source
    assert "Thought for a couple of seconds" in source
    assert "Thought for a few seconds" in source
    assert "_release_live_answer_matches_expected_single_token" in source
    assert "lines[-1] != expected_text" in source
    assert "all(line in cls._RELEASE_LIVE_VISIBLE_THINKING_PREAMBLES" in source

