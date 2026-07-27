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
        self.current_url = "https://chatgpt.com/g/g-p-demo/c/warmup?tab=sources"
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
        self.current_url = url
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
            "current_url": self.current_url,
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

    async def _wait_for_composer_ready_before_fill(self, page, *, timeout_ms: int = 20_000, poll_interval_ms: int = 500):  # type: ignore[no-untyped-def]
        return {
            "status": "composer_ready",
            "blockers": [],
            "send_ready": False,
            "stop_visible": False,
            "idle_visible": True,
            "thinking_state": {"visible": False},
            "interrupted_state": {"present": False},
        }

    def _dedicated_result_conversation_url(self, kwargs: dict) -> str:
        requested = str(kwargs.get("conversation_url") or "")
        if requested.endswith("/project"):
            return "https://chatgpt.com/g/g-p-demo/c/release-live-dedicated"
        return requested

    async def _ask_question_operation(self, **kwargs):  # type: ignore[no-untyped-def]
        self.ask_calls.append(dict(kwargs))
        conversation_url = (
            "https://chatgpt.com/g/g-p-demo/c/release-live-dedicated"
            if len(self.ask_calls) == 1
            else kwargs["conversation_url"]
        )
        self.current_url = conversation_url
        return {
            "ok": True,
            "status": "completed",
            "conversation_url": conversation_url,
            "answer": "ASK_SENTINEL" if len(self.ask_calls) == 2 else "BOOTSTRAP_SENTINEL",
        }

    async def _release_live_post_bootstrap_idle_recovery(self, page, *, conversation_url: str, bootstrap_prompt: str):  # type: ignore[no-untyped-def]
        return {
            "ok": True,
            "status": "post_bootstrap_conversation_idle",
            "conversation_url": conversation_url,
            "recovery_attempted": False,
            "recovery_count": 0,
            "bootstrap_resubmitted": False,
            "final_readiness": {"status": "composer_ready", "blockers": []},
        }


def test_release_live_continuous_trusted_conversation_skips_project_discovery(tmp_path: Path) -> None:
    client = DirectConversationClient(tmp_path)
    warmup_url = "https://chatgpt.com/g/g-p-demo/c/warmup?tab=sources"

    result = asyncio.run(
        client._release_live_bootstrap_and_ask_operation(
            context=object(),
            page=object(),
            project_name="promptbranch3",
            bootstrap_prompt="Reply with exactly the single token BOOTSTRAP_SENTINEL and nothing else.",
            ask_prompt="Reply with exactly the single token ASK_SENTINEL and nothing else.",
            icon=None,
            color=None,
            memory_mode="project-only",
            warmup_conversation_url=warmup_url,
        )
    )

    assert result["ok"] is True
    assert result["status"] == "completed"
    assert result["trusted_conversation_direct_mode"] is True
    assert result["root_project_discovery_skipped"] is True
    assert result["project_identity_source"] == "warmup_conversation_url"
    assert result["project_url"] == "https://chatgpt.com/g/g-p-demo/project"
    assert result["conversation_url"] == "https://chatgpt.com/g/g-p-demo/c/release-live-dedicated"
    assert result["trusted_conversation_mutation_avoided"] is True
    assert result["dedicated_release_live_conversation"] is True
    assert result["pre_bootstrap_idle_handoff"]["status"] == "dedicated_release_live_task_ready"
    assert result["pre_bootstrap_idle_handoff"]["stop_action_attempted"] is False
    assert result["project_result"]["status"] == "trusted_conversation_url"
    assert result["project_result"]["project_discovery_skipped"] is True
    assert len(client.goto_calls) == 2
    assert client.goto_calls[0] == {
        "url": warmup_url,
        "label": "release-live-continuous-trusted-conversation",
        "respect_history_rate_limit_cooldown": False,
    }
    assert client.goto_calls[1] == {
        "url": "https://chatgpt.com/g/g-p-demo/project",
        "label": "release-live-pre-bootstrap-idle-handoff",
        "respect_history_rate_limit_cooldown": False,
    }
    assert client.challenge_wait_labels == [
        "release-live-continuous-trusted-conversation",
        "release-live-pre-bootstrap-idle-handoff",
    ]
    assert client.fail_fast_stages == [
        "release-live-continuous-trusted-conversation",
        "release-live-pre-bootstrap-idle-handoff",
    ]
    assert result["project_result"]["trusted_conversation_ready"] is True
    assert result["project_result"]["trusted_conversation_readiness"]["composer_visible"] is True
    assert result["project_result"]["trusted_conversation_readiness"]["logged_in"] is True
    assert result["project_result"]["trusted_conversation_scope"]["matches"] is True
    assert len(client.ask_calls) == 2
    assert [call["conversation_url"] for call in client.ask_calls] == [
        "https://chatgpt.com/g/g-p-demo/project",
        "https://chatgpt.com/g/g-p-demo/c/release-live-dedicated",
    ]
    assert client.ask_calls[0]["reuse_current_page_if_ready"] is True
    assert client.ask_calls[1]["reuse_current_page_if_ready"] is True


def test_release_live_continuous_direct_conversation_static_guard() -> None:
    source = (Path(__file__).resolve().parents[1] / "promptbranch_browser_auth" / "client.py").read_text(encoding="utf-8")
    assert "using trusted project conversation URL directly; skipping root project discovery" in source
    assert "root_project_discovery_skipped" in source
    assert "project_identity_source\": \"warmup_conversation_url" in source
    assert "direct_conversation_mode = bool" in source
    assert "bootstrap_target_url = project_url" in source
    assert "_release_live_pre_bootstrap_idle_handoff" in source
    assert "release-live-pre-bootstrap-idle-handoff" in source
    assert "dedicated_release_live_task_ready" in source
    assert '"stop_action_attempted": False' in source
    assert 'conversation_url = None' in source
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
            "conversation_url": self._dedicated_result_conversation_url(kwargs),
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
                "conversation_url": self._dedicated_result_conversation_url(kwargs),
                "answer": "BOOTSTRAP_SENTINEL",
            }
        return {
            "status": "completed",
            "conversation_url": self._dedicated_result_conversation_url(kwargs),
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
    assert [call["conversation_url"] for call in client.ask_calls] == [
        "https://chatgpt.com/g/g-p-demo/project",
        "https://chatgpt.com/g/g-p-demo/project",
        "https://chatgpt.com/g/g-p-demo/c/release-live-dedicated",
    ]
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
                "conversation_url": self._dedicated_result_conversation_url(kwargs),
                "answer": "WRONG_BOOTSTRAP_SENTINEL",
            }
        if len(self.ask_calls) == 2:
            return {
                "status": "completed",
                "conversation_url": self._dedicated_result_conversation_url(kwargs),
                "answer": "ASK_SENTINEL",
            }
        return {
            "status": "completed",
            "conversation_url": self._dedicated_result_conversation_url(kwargs),
            "answer": "BOOTSTRAP_SENTINEL",
        }


class BootstrapSentinelMissingRetryFailureClient(DirectConversationClient):
    async def _ask_question_operation(self, **kwargs):  # type: ignore[no-untyped-def]
        self.ask_calls.append(dict(kwargs))
        if len(self.ask_calls) == 2:
            return {
                "status": "completed",
                "conversation_url": self._dedicated_result_conversation_url(kwargs),
                "answer": "ASK_SENTINEL",
            }
        return {
            "status": "completed",
            "conversation_url": self._dedicated_result_conversation_url(kwargs),
            "answer": "WRONG_BOOTSTRAP_SENTINEL",
        }


def test_release_live_continuous_stops_before_ask_when_bootstrap_sentinel_is_wrong(tmp_path: Path) -> None:
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

    assert result["ok"] is False
    assert result["status"] == "bootstrap_sentinel_missing_before_ask"
    assert result["failed_phase"] == "live_conversation_bootstrap"
    assert result["bootstrap_submission_succeeded"] is True
    assert result["bootstrap_generation_completed"] is True
    assert result["bootstrap_completed_with_expected_sentinel"] is False
    assert result["post_bootstrap_recovery_eligible"] is False
    assert result["post_bootstrap_idle_recovery"]["recovery_attempted"] is False
    assert result["ask_submission_attempted"] is False
    assert len(client.ask_calls) == 1


def test_release_live_continuous_wrong_bootstrap_never_runs_old_after_ask_retry(tmp_path: Path) -> None:
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
    assert result["status"] == "bootstrap_sentinel_missing_before_ask"
    assert result["failed_phase"] == "live_conversation_bootstrap"
    assert result["post_bootstrap_recovery_eligible"] is False
    assert result["ask_submission_attempted"] is False
    assert len(client.ask_calls) == 1


def test_release_live_continuous_bootstrap_sentinel_gate_static_guard() -> None:
    source = (Path(__file__).resolve().parents[1] / "promptbranch_browser_auth" / "client.py").read_text(encoding="utf-8")
    assert "bootstrap_sentinel_missing_before_ask" in source
    assert "post_bootstrap_recovery_eligible" in source
    assert "bootstrap_submission_succeeded" in source
    assert "bootstrap_generation_completed" in source
    assert "bootstrap_completed_with_expected_sentinel" in source
    assert '"ask_submission_attempted": False' in source


class VisibleThinkingPreambleCompletedSentinelClient(DirectConversationClient):
    async def _ask_question_operation(self, **kwargs):  # type: ignore[no-untyped-def]
        self.ask_calls.append(dict(kwargs))
        return {
            "status": "completed",
            "conversation_url": self._dedicated_result_conversation_url(kwargs),
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
                "conversation_url": self._dedicated_result_conversation_url(kwargs),
                "answer": "ASK_SENTINEL",
            }
        return {
            "status": "completed",
            "conversation_url": self._dedicated_result_conversation_url(kwargs),
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
    assert result["bootstrap_completed_with_expected_sentinel"] is True
    assert result["ask_completed_with_expected_sentinel"] is True


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
    assert result["status"] == "bootstrap_sentinel_missing_before_ask"
    assert result["failed_phase"] == "live_conversation_bootstrap"
    assert result["bootstrap_completed_with_expected_sentinel"] is False
    assert result["ask_submission_attempted"] is False
    assert len(client.ask_calls) == 1


def test_release_live_visible_thinking_preamble_normalization_static_guard() -> None:
    source = (Path(__file__).resolve().parents[1] / "promptbranch_browser_auth" / "client.py").read_text(encoding="utf-8")
    assert "_RELEASE_LIVE_VISIBLE_THINKING_PREAMBLES" in source
    assert "Thought for a couple of seconds" in source
    assert "Thought for a few seconds" in source
    assert "_release_live_answer_matches_expected_single_token" in source
    assert "lines[-1] != expected_text" in source
    assert "all(line in cls._RELEASE_LIVE_VISIBLE_THINKING_PREAMBLES" in source



class ReloadPage:
    def __init__(self, url: str) -> None:
        self.url = url
        self.reload_calls: list[dict] = []

    async def reload(self, *, wait_until: str, timeout: int):
        self.reload_calls.append({"wait_until": wait_until, "timeout": timeout})
        return None

    async def wait_for_timeout(self, ms: int):
        return None


class PostBootstrapInterruptedRecoveryClient(ChatGPTBrowserClient):
    def __init__(self, tmp_path: Path, *, final_ready: bool = True, initial_blockers: list[str] | None = None) -> None:
        super().__init__(
            ChatGPTBrowserConfig(
                project_url="https://chatgpt.com/g/g-p-demo/c/warmup",
                profile_dir=str(tmp_path / "profile"),
                debug_artifact_dir=str(tmp_path / "debug"),
            )
        )
        self.final_ready = final_ready
        self.initial_blockers = initial_blockers or ["interrupted_answer_state"]
        self.readiness_calls = 0
        self.challenge_wait_labels: list[str] = []
        self.fail_fast_stages: list[str] = []

    def _log(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        return None

    async def _wait_for_composer_ready_before_fill(self, page, *, timeout_ms: int = 20_000, poll_interval_ms: int = 500):  # type: ignore[no-untyped-def]
        self.readiness_calls += 1
        if self.readiness_calls == 1:
            return {
                "status": "composer_not_ready_before_fill",
                "blockers": list(self.initial_blockers),
                "stop_visible": "stop_button_visible" in self.initial_blockers,
                "thinking_state": {"visible": "thinking_visible" in self.initial_blockers},
                "interrupted_state": {"present": "interrupted_answer_state" in self.initial_blockers},
            }
        if self.final_ready:
            return {
                "status": "composer_ready",
                "blockers": [],
                "stop_visible": False,
                "thinking_state": {"visible": False},
                "interrupted_state": {"present": False},
            }
        return {
            "status": "composer_not_ready_before_fill",
            "blockers": ["interrupted_answer_state"],
            "stop_visible": False,
            "thinking_state": {"visible": False},
            "interrupted_state": {"present": True},
        }

    async def _safe_page_url(self, page):  # type: ignore[no-untyped-def]
        return page.url

    async def _wait_for_challenge_resolution(self, page, *, label: str):  # type: ignore[no-untyped-def]
        self.challenge_wait_labels.append(label)

    async def _raise_fail_fast_challenge_if_configured(self, page, *, stage: str):  # type: ignore[no-untyped-def]
        self.fail_fast_stages.append(stage)

    async def _extract_last_text_from_selectors(self, page, selectors):  # type: ignore[no-untyped-def]
        return '[data-message-author-role="assistant"]', 2, "BOOTSTRAP_SENTINEL", []

    async def _release_live_wait_for_conversation_hydration(self, page, *, expected_bootstrap_token: str, timeout_ms: int = 15_000, poll_interval_ms: int = 500):  # type: ignore[no-untyped-def]
        return {
            "ok": True,
            "status": "conversation_hydrated",
            "assistant_selector": '[data-message-author-role="assistant"]',
            "assistant_count": 2,
            "assistant_text": "BOOTSTRAP_SENTINEL",
            "assistant_probes": [],
            "composer_visible": True,
            "bootstrap_sentinel_visible": True,
            "attempt_count": 1,
        }


def test_release_live_post_bootstrap_interrupted_state_reloads_same_conversation_once(tmp_path: Path) -> None:
    url = "https://chatgpt.com/g/g-p-demo/c/warmup"
    page = ReloadPage(url)
    client = PostBootstrapInterruptedRecoveryClient(tmp_path, final_ready=True)

    result = asyncio.run(
        client._release_live_post_bootstrap_idle_recovery(
            page,
            conversation_url=url,
            bootstrap_prompt="Reply with exactly the single token BOOTSTRAP_SENTINEL and nothing else.",
        )
    )

    assert result["ok"] is True
    assert result["status"] == "post_bootstrap_conversation_idle_recovered"
    assert result["recovery_attempted"] is True
    assert result["recovery_count"] == 1
    assert result["bootstrap_resubmitted"] is False
    assert result["new_conversation_created"] is False
    assert result["same_page_reused"] is True
    assert result["continuous_browser_context_preserved"] is True
    assert result["physical_profile_preserved"] is True
    assert result["same_conversation_scope"]["matches"] is True
    assert result["bootstrap_sentinel_reverified_after_reload"] is True
    assert result["stop_thinking_running_absent"] is True
    assert result["final_blockers"] == []
    assert page.reload_calls == [{"wait_until": "domcontentloaded", "timeout": 30_000}]
    assert client.readiness_calls == 2
    assert client.challenge_wait_labels == ["release-live-post-bootstrap-idle-recovery"]
    assert client.fail_fast_stages == ["release-live-post-bootstrap-idle-recovery"]


def test_release_live_post_bootstrap_interrupted_state_persists_fails_closed_after_one_reload(tmp_path: Path) -> None:
    url = "https://chatgpt.com/g/g-p-demo/c/warmup"
    page = ReloadPage(url)
    client = PostBootstrapInterruptedRecoveryClient(tmp_path, final_ready=False)

    result = asyncio.run(
        client._release_live_post_bootstrap_idle_recovery(
            page,
            conversation_url=url,
            bootstrap_prompt="Reply with exactly the single token BOOTSTRAP_SENTINEL and nothing else.",
        )
    )

    assert result["ok"] is False
    assert result["status"] == "target_conversation_busy"
    assert result["recovery_attempted"] is True
    assert result["recovery_count"] == 1
    assert result["bootstrap_resubmitted"] is False
    assert result["final_blockers"] == ["interrupted_answer_state"]
    assert page.reload_calls == [{"wait_until": "domcontentloaded", "timeout": 30_000}]
    assert client.readiness_calls == 2


def test_release_live_post_bootstrap_does_not_reload_for_other_busy_blockers(tmp_path: Path) -> None:
    url = "https://chatgpt.com/g/g-p-demo/c/warmup"
    page = ReloadPage(url)
    client = PostBootstrapInterruptedRecoveryClient(
        tmp_path,
        initial_blockers=["stop_button_visible", "interrupted_answer_state"],
    )

    result = asyncio.run(
        client._release_live_post_bootstrap_idle_recovery(
            page,
            conversation_url=url,
            bootstrap_prompt="Reply with exactly the single token BOOTSTRAP_SENTINEL and nothing else.",
        )
    )

    assert result["ok"] is False
    assert result["status"] == "target_conversation_busy"
    assert result["recovery_attempted"] is False
    assert result["recovery_skipped_reason"] == "readiness_blocker_not_interrupted_answer_state_only"
    assert page.reload_calls == []
    assert client.readiness_calls == 1


class PostBootstrapRecoveryFailureContinuousClient(DirectConversationClient):
    async def _release_live_post_bootstrap_idle_recovery(self, page, *, conversation_url: str, bootstrap_prompt: str):  # type: ignore[no-untyped-def]
        return {
            "ok": False,
            "status": "target_conversation_busy",
            "conversation_url": conversation_url,
            "recovery_attempted": True,
            "recovery_count": 1,
            "bootstrap_resubmitted": False,
            "final_blockers": ["interrupted_answer_state"],
        }


def test_release_live_continuous_does_not_submit_ask_when_post_bootstrap_recovery_fails(tmp_path: Path) -> None:
    client = PostBootstrapRecoveryFailureContinuousClient(tmp_path)
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
    assert result["status"] == "target_conversation_busy"
    assert result["failed_phase"] == "ask_live"
    assert result["ask_submission_attempted"] is False
    assert result["post_bootstrap_idle_recovery"]["recovery_count"] == 1
    assert len(client.ask_calls) == 1
    assert client.ask_calls[0]["prompt"] == "Reply with exactly the single token BOOTSTRAP_SENTINEL and nothing else."


def test_release_live_post_bootstrap_recovery_static_contract() -> None:
    source = (Path(__file__).resolve().parents[1] / "promptbranch_browser_auth" / "client.py").read_text(encoding="utf-8")
    assert "_release_live_post_bootstrap_idle_recovery" in source
    assert 'initial_blockers == ["interrupted_answer_state"]' in source
    assert 'await page.reload(wait_until="domcontentloaded", timeout=30_000)' in source
    assert "release-live-post-bootstrap-idle-recovery" in source
    assert "bootstrap_sentinel_reverified_after_reload" in source
    assert "_release_live_wait_for_conversation_hydration" in source
    assert "conversation_hydration" in source
    assert "stop_thinking_running_absent" in source
    assert '"ask_submission_attempted": False' in source
    assert '"status": "target_conversation_busy"' in source

class BootstrapIncompleteNoRecoveryClient(DirectConversationClient):
    def __init__(self, tmp_path: Path) -> None:
        super().__init__(tmp_path)
        self.recovery_calls = 0

    async def _ask_question_operation(self, **kwargs):  # type: ignore[no-untyped-def]
        self.ask_calls.append(dict(kwargs))
        return {
            "ok": False,
            "status": "target_conversation_busy",
            "conversation_url": self._dedicated_result_conversation_url(kwargs),
            "answer": "",
        }

    async def _release_live_post_bootstrap_idle_recovery(self, page, *, conversation_url: str, bootstrap_prompt: str):  # type: ignore[no-untyped-def]
        self.recovery_calls += 1
        raise AssertionError("post-bootstrap recovery must not run before a completed bootstrap sentinel")


def test_release_live_continuous_never_invokes_post_bootstrap_recovery_for_incomplete_bootstrap(tmp_path: Path) -> None:
    client = BootstrapIncompleteNoRecoveryClient(tmp_path)
    warmup_url = "https://chatgpt.com/g/g-p-demo/c/warmup?tab=sources"

    result = asyncio.run(
        client._release_live_bootstrap_and_ask_operation(
            context=object(),
            page=object(),
            project_name="promptbranch3",
            bootstrap_prompt="Reply with exactly the single token BOOTSTRAP_SENTINEL and nothing else.",
            ask_prompt="Reply with exactly the single token ASK_SENTINEL and nothing else.",
            icon=None,
            color=None,
            memory_mode="project-only",
            warmup_conversation_url=warmup_url,
        )
    )

    assert result["ok"] is False
    assert result["status"] == "target_conversation_busy"
    assert result["failed_phase"] == "live_conversation_bootstrap"
    assert result["bootstrap_submission_succeeded"] is False
    assert result["bootstrap_generation_completed"] is False
    assert result["bootstrap_completed_with_expected_sentinel"] is False
    assert result["post_bootstrap_recovery_eligible"] is False
    assert result["post_bootstrap_idle_recovery"]["status"] == "post_bootstrap_recovery_not_applicable"
    assert result["post_bootstrap_idle_recovery"]["recovery_attempted"] is False
    assert result["ask_submission_attempted"] is False
    assert client.recovery_calls == 0
    assert len(client.ask_calls) == 1


class HydrationWaitClient(ChatGPTBrowserClient):
    def __init__(self, tmp_path: Path) -> None:
        super().__init__(
            ChatGPTBrowserConfig(
                project_url="https://chatgpt.com/g/g-p-demo/c/warmup",
                profile_dir=str(tmp_path / "profile"),
                debug_artifact_dir=str(tmp_path / "debug"),
            )
        )
        self.extract_calls = 0

    def _log(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        return None

    async def _extract_last_text_from_selectors(self, page, selectors):  # type: ignore[no-untyped-def]
        self.extract_calls += 1
        if self.extract_calls == 1:
            return None, 0, "", []
        return '[data-message-author-role="assistant"]', 2, "BOOTSTRAP_SENTINEL", []

    async def _chat_input_visible(self, page):  # type: ignore[no-untyped-def]
        return self.extract_calls >= 2


def test_release_live_reload_waits_for_bounded_conversation_hydration(tmp_path: Path) -> None:
    client = HydrationWaitClient(tmp_path)
    page = ReloadPage("https://chatgpt.com/g/g-p-demo/c/warmup")

    result = asyncio.run(
        client._release_live_wait_for_conversation_hydration(
            page,
            expected_bootstrap_token="BOOTSTRAP_SENTINEL",
            timeout_ms=100,
            poll_interval_ms=1,
        )
    )

    assert result["ok"] is True
    assert result["status"] == "conversation_hydrated"
    assert result["attempt_count"] == 2
    assert result["assistant_count"] == 2
    assert result["bootstrap_sentinel_visible"] is True
    assert result["composer_visible"] is True


def test_release_live_current_turn_interruption_scope_static_contract() -> None:
    source = (Path(__file__).resolve().parents[1] / "promptbranch_browser_auth" / "client.py").read_text(encoding="utf-8")
    assert 'scope: "latest_assistant_turn_or_active_composer"' in source
    assert "historical_controls_ignored" in source
    assert "latestTurn.contains(item.node)" in source
    assert "post_bootstrap_recovery_eligible" in source
    assert '"reason": "bootstrap_not_completed_with_expected_sentinel"' in source
    assert "_release_live_wait_for_conversation_hydration" in source


class BusyTrustedConversationHandoffClient(DirectConversationClient):
    def __init__(self, tmp_path: Path, *, final_ready: bool) -> None:
        super().__init__(tmp_path)
        self.final_ready = final_ready
        self.handoff_readiness_calls = 0

    async def _wait_for_composer_ready_before_fill(self, page, *, timeout_ms: int = 20_000, poll_interval_ms: int = 500):  # type: ignore[no-untyped-def]
        self.handoff_readiness_calls += 1
        if self.handoff_readiness_calls == 1:
            return {
                "status": "composer_not_ready_before_fill",
                "blockers": ["stop_button_visible"],
                "send_ready": False,
                "stop_visible": True,
                "idle_visible": False,
                "thinking_state": {"visible": False},
                "interrupted_state": {"present": False},
            }
        if self.final_ready:
            return {
                "status": "composer_ready",
                "blockers": [],
                "send_ready": False,
                "stop_visible": False,
                "idle_visible": True,
                "thinking_state": {"visible": False},
                "interrupted_state": {"present": False},
            }
        return {
            "status": "composer_not_ready_before_fill",
            "blockers": ["stop_button_visible"],
            "send_ready": False,
            "stop_visible": True,
            "idle_visible": False,
            "thinking_state": {"visible": False},
            "interrupted_state": {"present": False},
        }


def test_release_live_busy_trusted_conversation_hands_off_to_dedicated_project_task(tmp_path: Path) -> None:
    client = BusyTrustedConversationHandoffClient(tmp_path, final_ready=True)
    warmup_url = "https://chatgpt.com/g/g-p-demo/c/warmup?tab=sources"

    result = asyncio.run(
        client._release_live_bootstrap_and_ask_operation(
            context=object(),
            page=object(),
            project_name="promptbranch3",
            bootstrap_prompt="Reply with exactly the single token BOOTSTRAP_SENTINEL and nothing else.",
            ask_prompt="Reply with exactly the single token ASK_SENTINEL and nothing else.",
            icon=None,
            color=None,
            memory_mode="project-only",
            warmup_conversation_url=warmup_url,
        )
    )

    assert result["ok"] is True
    handoff = result["pre_bootstrap_idle_handoff"]
    assert handoff["trusted_conversation_initial_blockers"] == ["stop_button_visible"]
    assert handoff["trusted_conversation_initial_idle"] is False
    assert handoff["status"] == "dedicated_release_live_task_ready"
    assert handoff["bootstrap_target_url"] == "https://chatgpt.com/g/g-p-demo/project"
    assert handoff["stop_action_attempted"] is False
    assert handoff["trusted_conversation_mutation_avoided"] is True
    assert client.ask_calls[0]["conversation_url"] == "https://chatgpt.com/g/g-p-demo/project"
    assert result["conversation_url"] == "https://chatgpt.com/g/g-p-demo/c/release-live-dedicated"


def test_release_live_idle_handoff_failure_stops_before_bootstrap_submission(tmp_path: Path) -> None:
    client = BusyTrustedConversationHandoffClient(tmp_path, final_ready=False)
    warmup_url = "https://chatgpt.com/g/g-p-demo/c/warmup?tab=sources"

    result = asyncio.run(
        client._release_live_bootstrap_and_ask_operation(
            context=object(),
            page=object(),
            project_name="promptbranch3",
            bootstrap_prompt="Reply with exactly the single token BOOTSTRAP_SENTINEL and nothing else.",
            ask_prompt="Reply with exactly the single token ASK_SENTINEL and nothing else.",
            icon=None,
            color=None,
            memory_mode="project-only",
            warmup_conversation_url=warmup_url,
        )
    )

    assert result["ok"] is False
    assert result["status"] == "release_live_idle_handoff_failed"
    assert result["failed_phase"] == "live_conversation_bootstrap"
    assert result["bootstrap_submission_attempted"] is False
    assert result["ask_submission_attempted"] is False
    assert result["pre_bootstrap_idle_handoff"]["handoff_final_blockers"] == ["stop_button_visible"]
    assert result["pre_bootstrap_idle_handoff"]["stop_action_attempted"] is False
    assert client.ask_calls == []
