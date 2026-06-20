from __future__ import annotations

from pathlib import Path

from promptbranch_browser_auth.client import ChatGPTBrowserClient
from promptbranch_browser_auth.config import ChatGPTBrowserConfig


def _make_client(tmp_path: Path) -> ChatGPTBrowserClient:
    config = ChatGPTBrowserConfig(
        project_url="https://chatgpt.com/",
        profile_dir=str(tmp_path / ".pb_profile"),
        debug=False,
        save_trace=False,
        save_html=False,
        save_screenshot=False,
    )
    return ChatGPTBrowserClient(config)



def test_protocol_submit_turn_probe_selectors_include_generic_fallbacks(tmp_path: Path) -> None:
    from promptbranch_browser_auth.client import GENERIC_CONVERSATION_TURN_SELECTORS, USER_MESSAGE_SELECTORS

    assert '[data-message-author-role="user"]' in USER_MESSAGE_SELECTORS
    assert 'article:has([data-message-author-role="user"])' in USER_MESSAGE_SELECTORS
    assert '[data-testid*="conversation-turn"]' in GENERIC_CONVERSATION_TURN_SELECTORS
    assert 'main article' in GENERIC_CONVERSATION_TURN_SELECTORS

def test_response_completion_ready_after_observed_run_then_idle(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    assert client._response_completion_signal_ready(
        current_url="https://chatgpt.com/c/abc123",
        content_present=True,
        stop_visible=False,
        thinking_visible=False,
        composer_idle_visible=True,
        observed_running_state=True,
        observed_idle_after_running=True,
    ) is True


def test_response_completion_ready_requires_composer_idle_after_observed_run(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    assert client._response_completion_signal_ready(
        current_url="https://chatgpt.com/c/abc123",
        content_present=True,
        stop_visible=False,
        thinking_visible=False,
        composer_idle_visible=False,
        observed_running_state=True,
        observed_idle_after_running=True,
    ) is False


def test_response_completion_ready_uses_idle_text_fallback_on_conversation_url(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    assert client._response_completion_signal_ready(
        current_url="https://chatgpt.com/g/g-p-1234567890abcdef/project/c/abc123".replace("/project/c/", "/c/"),
        content_present=True,
        stop_visible=False,
        thinking_visible=False,
        composer_idle_visible=True,
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
        composer_idle_visible=True,
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
        composer_idle_visible=True,
        observed_running_state=False,
        observed_idle_after_running=False,
    ) is False
    assert client._response_completion_signal_ready(
        current_url="https://chatgpt.com/c/abc123",
        content_present=True,
        stop_visible=False,
        thinking_visible=True,
        composer_idle_visible=True,
        observed_running_state=False,
        observed_idle_after_running=False,
    ) is False


class _CompletionProbeTriggered(Exception):
    def __init__(self, content_present: bool) -> None:
        super().__init__(str(content_present))
        self.content_present = content_present


def test_wait_and_get_response_passes_candidate_text_as_content_present(tmp_path: Path, monkeypatch) -> None:
    client = _make_client(tmp_path)

    class DummyPage:
        async def wait_for_timeout(self, _ms: int) -> None:
            return None

    async def fake_open_new_project_conversation(*args, **kwargs) -> None:
        return None

    async def fake_extract_last_text_from_selectors(*args, **kwargs):
        return 'assistant', 1, 'INTEGRATION_OK', []

    async def fake_probe_submit_button_state(*args, **kwargs):
        return {
            'selector': '#composer-submit-button',
            'send_ready': True,
            'idle_visible': True,
            'visible_enabled_count': 1,
            'aria_label': 'Send prompt',
            'data_testid': 'send-button',
            'stop_visible': False,
        }

    async def fake_probe_thinking_state(*args, **kwargs):
        return {'visible': False, 'text': ''}

    async def fake_safe_page_url(*args, **kwargs):
        return 'https://chatgpt.com/c/test-conversation'

    def fake_completion_signal_ready(*, content_present: bool, **kwargs):
        raise _CompletionProbeTriggered(content_present)

    monkeypatch.setattr(client, '_maybe_open_new_project_conversation', fake_open_new_project_conversation)
    monkeypatch.setattr(client, '_extract_last_text_from_selectors', fake_extract_last_text_from_selectors)
    monkeypatch.setattr(client, '_probe_submit_button_state', fake_probe_submit_button_state)
    monkeypatch.setattr(client, '_probe_thinking_state', fake_probe_thinking_state)
    monkeypatch.setattr(client, '_safe_page_url', fake_safe_page_url)
    monkeypatch.setattr(client, '_response_completion_signal_ready', fake_completion_signal_ready)

    try:
        import asyncio
        asyncio.run(client._wait_and_get_response(DummyPage()))
    except _CompletionProbeTriggered as exc:
        assert exc.content_present is True
    else:
        raise AssertionError('expected completion probe to trigger')


def test_run_with_context_preserves_original_exception_when_operation_fails(tmp_path: Path, monkeypatch) -> None:
    client = _make_client(tmp_path)

    class DummyTracing:
        async def start(self, **kwargs) -> None:
            return None

    class DummyPage:
        pass

    class DummyContext:
        def __init__(self) -> None:
            self.pages = [DummyPage()]
            self.tracing = DummyTracing()

        def set_default_timeout(self, _timeout: int) -> None:
            return None

        def on(self, _event: str, _handler) -> None:
            return None

    class DummyChromium:
        async def launch_persistent_context(self, **kwargs):
            return DummyContext()

    class DummyPlaywright:
        def __init__(self) -> None:
            self.chromium = DummyChromium()

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

    async def fake_operation(**kwargs):
        raise ValueError('boom')

    async def fake_safe_page_url(*args, **kwargs):
        return 'https://chatgpt.com/c/test-conversation'

    async def fake_dump_failure_artifacts(*args, **kwargs) -> None:
        return None

    async def fake_finalize_context(*args, **kwargs) -> None:
        return None

    async def fake_start_driver():
        return DummyPlaywright()

    monkeypatch.setattr(client, '_start_driver', fake_start_driver)
    monkeypatch.setattr(client, '_safe_page_url', fake_safe_page_url)
    monkeypatch.setattr(client, '_dump_failure_artifacts', fake_dump_failure_artifacts)
    monkeypatch.setattr(client, '_finalize_context', fake_finalize_context)

    import asyncio

    try:
        asyncio.run(client._run_with_context('failing-operation', fake_operation))
    except ValueError as exc:
        assert str(exc) == 'boom'
    else:
        raise AssertionError('expected original ValueError to be raised')


class _FakeLastLocator:
    def __init__(self, visible: bool) -> None:
        self._visible = visible

    async def is_visible(self, timeout: int = 1_000) -> bool:
        return self._visible


class _FakeLocator:
    def __init__(self, count: int, texts: list[str], *, visible: bool = False) -> None:
        self._count = count
        self._texts = texts
        self.last = _FakeLastLocator(visible)

    async def count(self) -> int:
        return self._count

    async def evaluate_all(self, _script: str):
        return list(self._texts)


class _FakePage:
    def __init__(self, selector_map: dict[str, tuple[int, list[str], bool]]) -> None:
        self._selector_map = selector_map

    def locator(self, selector: str) -> _FakeLocator:
        count, texts, visible = self._selector_map.get(selector, (0, [], False))
        return _FakeLocator(count, texts, visible=visible)


def test_extract_last_text_from_selectors_supports_section_assistant_turns(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    page = _FakePage(
        {
            '[data-message-author-role="assistant"]': (1, [''], False),
            'section[data-testid*="conversation-turn"][data-turn="assistant"]': (1, ['1 + 1 = 2'], True),
        }
    )

    import asyncio

    selector, count, text, probes = asyncio.run(client._extract_last_text_from_selectors(page, client_module_selectors()))

    assert selector == 'section[data-testid*="conversation-turn"][data-turn="assistant"]'
    assert count == 1
    assert text == '1 + 1 = 2'
    assert any(probe['selector'] == selector and probe['text_length'] == len(text) for probe in probes)


def client_module_selectors() -> list[str]:
    from promptbranch_browser_auth.client import ASSISTANT_MESSAGE_SELECTORS

    return ASSISTANT_MESSAGE_SELECTORS


def test_response_completion_ready_uses_stable_text_fallback_when_composer_selector_missing(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    assert client._response_completion_signal_ready(
        current_url="https://chatgpt.com/g/g-p-demo/c/abc123",
        content_present=True,
        stop_visible=False,
        thinking_visible=False,
        composer_idle_visible=False,
        composer_signal_known=False,
        fallback_stable_ready=True,
        observed_running_state=True,
        observed_idle_after_running=True,
    ) is True


def test_response_completion_ready_does_not_use_missing_composer_without_fallback(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    assert client._response_completion_signal_ready(
        current_url="https://chatgpt.com/g/g-p-demo/c/abc123",
        content_present=True,
        stop_visible=False,
        thinking_visible=False,
        composer_idle_visible=False,
        composer_signal_known=False,
        fallback_stable_ready=False,
        observed_running_state=True,
        observed_idle_after_running=True,
    ) is False


def test_run_with_context_retries_recoverable_browser_context_launch_once(tmp_path: Path, monkeypatch) -> None:
    client = _make_client(tmp_path)

    class DummyTracing:
        async def start(self, **kwargs) -> None:
            return None

    class DummyPage:
        pass

    class DummyContext:
        def __init__(self) -> None:
            self.pages = [DummyPage()]
            self.tracing = DummyTracing()

        def set_default_timeout(self, _timeout: int) -> None:
            return None

        def on(self, _event: str, _handler) -> None:
            return None

    class DummyChromium:
        def __init__(self) -> None:
            self.calls = 0

        async def launch_persistent_context(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError('Target page, context or browser has been closed. Opening in existing browser session.')
            return DummyContext()

    chromium = DummyChromium()

    class DummyPlaywright:
        def __init__(self) -> None:
            self.chromium = chromium

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

    async def fake_operation(**kwargs):
        return {'ok': True}

    async def fake_finalize_context(*args, **kwargs) -> None:
        return None

    async def fake_start_driver():
        return DummyPlaywright()

    monkeypatch.setattr(client, '_start_driver', fake_start_driver)
    monkeypatch.setattr(client, '_finalize_context', fake_finalize_context)
    monkeypatch.setattr(client, '_clear_profile_singleton_locks', lambda: ['SingletonLock'])

    import asyncio

    result = asyncio.run(client._run_with_context('launch-retry-operation', fake_operation))

    assert result['ok'] is True
    assert chromium.calls == 2


def test_run_with_context_classifies_unrecoverable_browser_context_launch(tmp_path: Path, monkeypatch) -> None:
    from promptbranch_browser_auth.exceptions import BrowserContextUnavailableError

    client = _make_client(tmp_path)

    class DummyChromium:
        def __init__(self) -> None:
            self.calls = 0

        async def launch_persistent_context(self, **kwargs):
            self.calls += 1
            raise RuntimeError('Target page, context or browser has been closed. Opening in existing browser session.')

    chromium = DummyChromium()

    class DummyPlaywright:
        def __init__(self) -> None:
            self.chromium = chromium

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

    async def fake_operation(**kwargs):
        return {'ok': True}

    async def fake_start_driver():
        return DummyPlaywright()

    monkeypatch.setattr(client, '_start_driver', fake_start_driver)
    monkeypatch.setattr(client, '_clear_profile_singleton_locks', lambda: ['SingletonLock'])

    import asyncio

    try:
        asyncio.run(client._run_with_context('launch-failure-operation', fake_operation))
    except BrowserContextUnavailableError as exc:
        assert 'browser_context_unavailable' in str(exc)
    else:
        raise AssertionError('expected BrowserContextUnavailableError')

    assert chromium.calls == 2


def test_response_completion_idle_selectors_include_use_voice() -> None:
    from promptbranch_browser_auth.client import COMPOSER_IDLE_INDICATOR_SELECTORS

    assert '#thread-bottom button[aria-label="Use Voice"]' in COMPOSER_IDLE_INDICATOR_SELECTORS
    assert 'button[aria-label="Use Voice"]' in COMPOSER_IDLE_INDICATOR_SELECTORS


def test_response_completion_treats_use_voice_as_idle_label(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    assert client._is_idle_composer_label('Use Voice') is True
    assert client._is_idle_composer_label('Start Voice') is True
    assert client._is_idle_composer_label('Start dictation') is True


def test_response_completion_predicate_logging_explains_missing_idle(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    blockers = client._response_completion_predicate_blockers(
        current_url='https://chatgpt.com/c/abc123',
        content_present=True,
        stop_visible=False,
        thinking_visible=False,
        composer_idle_visible=False,
        composer_signal_known=True,
        fallback_stable_ready=False,
        observed_running_state=True,
        observed_idle_after_running=False,
        stable_polls=0,
        stable_required=3,
        stable_elapsed_s=0.0,
        strong_idle_completion=False,
    )

    assert 'composer_idle_signal_missing' in blockers
    assert 'stable_polls_below_required' in blockers


def test_response_completion_predicate_logging_does_not_block_strong_idle(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    blockers = client._response_completion_predicate_blockers(
        current_url='https://chatgpt.com/c/abc123',
        content_present=True,
        stop_visible=False,
        thinking_visible=False,
        composer_idle_visible=True,
        composer_signal_known=True,
        fallback_stable_ready=False,
        observed_running_state=True,
        observed_idle_after_running=True,
        stable_polls=0,
        stable_required=3,
        stable_elapsed_s=0.0,
        strong_idle_completion=True,
    )

    assert 'stable_polls_below_required' not in blockers
    assert 'minimum_completion_delay_not_met' not in blockers


def test_headed_patchright_uses_linux_x11_vulkan_safe_args(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client.config.headless = False
    client.config.use_patchright = True

    args = client._effective_browser_args()

    assert "--ozone-platform=x11" in args
    assert "--disable-gpu" in args
    assert "--disable-vulkan" in args


def test_headless_patchright_does_not_add_headed_safe_args(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client.config.headless = True
    client.config.use_patchright = True

    args = client._effective_browser_args()

    assert "--ozone-platform=x11" not in args
    assert "--disable-gpu" not in args
    assert "--disable-vulkan" not in args


def test_run_with_context_wraps_patchright_launch_crash_as_structured_payload(tmp_path: Path, monkeypatch) -> None:
    from promptbranch_browser_auth.exceptions import BrowserContextUnavailableError

    client = _make_client(tmp_path)
    client.config.headless = False
    client.config.use_patchright = True

    class DummyChromium:
        async def launch_persistent_context(self, **kwargs):
            raise RuntimeError("Protocol error (Network.setCacheDisabled): Internal server error, session closed")

    class DummyPlaywright:
        def __init__(self) -> None:
            self.chromium = DummyChromium()

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

    async def fake_start_driver():
        return DummyPlaywright()

    async def fake_operation(**kwargs):
        return {"ok": True}

    monkeypatch.setattr(client, "_start_driver", fake_start_driver)

    import asyncio

    try:
        asyncio.run(client._run_with_context("launch-crash-operation", fake_operation))
    except BrowserContextUnavailableError as exc:
        payload = exc.to_payload()
    else:
        raise AssertionError("expected BrowserContextUnavailableError")

    assert payload["status"] == "browser_launch_failed"
    assert payload["browser_driver"] == "patchright"
    assert payload["browser_mode"] == "local_headed_patchright"
    assert payload["likely_linux_gpu_backend_issue"] is True
    assert "--ozone-platform=x11" in payload["browser_args"]


def test_attachment_visible_answer_promotes_after_unconfirmed_submit(tmp_path: Path) -> None:
    import asyncio

    client = _make_client(tmp_path)

    class DummyPage:
        pass

    async def fake_safe_page_url(page):
        return "https://chatgpt.com/g/g-p-6a1af3fe64a481919a2cc7de3cff0487-ask-live-temp/c/6a1b"

    async def fake_wait_and_get_response(page, *, response_context=None):
        if response_context is not None:
            response_context["last_response_extraction_mode"] = "assistant_selector"
            response_context["last_response_extraction_seconds"] = 0.123
        return "ASK_LIVE_FILE_ATTACHMENT_UNIT"

    client._safe_page_url = fake_safe_page_url
    client._wait_and_get_response = fake_wait_and_get_response

    submit_evidence = {
        "submit_confirmed": False,
        "submit_confirmed_by": [],
        "submit_confirmation_mode": "network_submit_request_timeout",
    }
    phase_timings = {}
    response_context = {"assistant_count": 0}

    result = asyncio.run(client._try_promote_attachment_visible_answer_after_unconfirmed_submit(
        DummyPage(),
        upload_paths=["/tmp/ask_live_attachment.txt"],
        response_context=response_context,
        submit_evidence=submit_evidence,
        phase_timings=phase_timings,
        operation_started=0.0,
    ))

    assert result is not None
    assert result["status"] == "completed"
    assert result["answer"] == "ASK_LIVE_FILE_ATTACHMENT_UNIT"
    assert result["conversation_url"].endswith("/c/6a1b")
    assert result["submit_evidence"]["submit_confirmed"] is True
    assert result["submit_evidence"]["submit_confirmation_mode"] == "attachment_visible_answer_after_unconfirmed_submit"
    assert "attachment_visible_answer" in result["submit_evidence"]["submit_confirmed_by"]
    assert result["submit_causality_confirmed"] is True
    assert result["submit_backend_commit_confirmed"] is True
    assert result["submit_backend_commit_confirmation_mode"] == "attachment_visible_answer_equivalent"
    assert result["response_causality_confirmed"] is True
    assert result["response_causality_mode"] == "attachment_visible_answer_after_unconfirmed_submit"
    assert result["answer_text_length"] == len("ASK_LIVE_FILE_ATTACHMENT_UNIT")
    assert phase_timings["attachment_visible_answer_fallback_status"] == "visible_answer_promoted"
    assert phase_timings["response_freshness_verified"] is True


def test_attachment_visible_answer_project_home_waits_for_project_conversation(tmp_path: Path) -> None:
    import asyncio

    client = _make_client(tmp_path)

    class DummyPage:
        pass

    urls = iter([
        "https://chatgpt.com/g/g-p-6a1af3fe64a481919a2cc7de3cff0487/project",
        "https://chatgpt.com/g/g-p-6a1af3fe64a481919a2cc7de3cff0487/c/6a1b",
    ])

    async def fake_safe_page_url(page):
        return next(urls)

    async def fake_wait_and_get_response(page, *, response_context=None):
        if response_context is not None:
            response_context["last_response_extraction_mode"] = "project_conversation_follow"
        return "VISUAL_ARTIFACT_ROUNDTRIP_REPLY"

    client._safe_page_url = fake_safe_page_url
    client._wait_and_get_response = fake_wait_and_get_response

    phase_timings = {}
    response_context = {"assistant_count": 0}
    submit_evidence = {"submit_confirmed": False, "submit_confirmed_by": []}

    result = asyncio.run(client._try_promote_attachment_visible_answer_after_unconfirmed_submit(
        DummyPage(),
        upload_paths=["/tmp/pb_visual_artifact_roundtrip_input.zip"],
        response_context=response_context,
        submit_evidence=submit_evidence,
        phase_timings=phase_timings,
        operation_started=0.0,
    ))

    assert result is not None
    assert result["status"] == "completed"
    assert result["conversation_url"].endswith("/c/6a1b")
    assert result["answer"] == "VISUAL_ARTIFACT_ROUNDTRIP_REPLY"
    assert phase_timings["attachment_visible_answer_fallback_project_home_wait_allowed"] is True
    assert phase_timings["attachment_visible_answer_fallback_post_response_url"].endswith("/c/6a1b")
    assert phase_timings["attachment_visible_answer_fallback_status"] == "visible_answer_promoted"



def test_attachment_submit_ready_waits_for_enabled_send_button(tmp_path: Path) -> None:
    import asyncio

    client = _make_client(tmp_path)

    class DummyPage:
        def __init__(self) -> None:
            self.waits = 0

        async def wait_for_timeout(self, ms):
            self.waits += 1

    page = DummyPage()
    states = iter([
        {"send_ready": False, "stop_visible": False, "idle_visible": True, "selector": "button[aria-label=Start Voice]", "aria_label": "Start Voice", "visible": True, "enabled": True},
        {"send_ready": True, "stop_visible": False, "idle_visible": False, "selector": "#composer-submit-button", "aria_label": "Send prompt", "visible": True, "enabled": True},
    ])

    async def fake_probe(_page):
        return next(states)

    client._probe_submit_button_state = fake_probe
    result = asyncio.run(client._wait_for_attachment_submit_ready(page, timeout_ms=1_000, poll_interval_ms=1))

    assert result["ready"] is True
    assert result["status"] == "attachment_submit_ready"
    assert result["attempt_count"] == 2
    assert page.waits == 1


def test_attachment_visible_answer_fallback_skips_non_attachment_unconfirmed_submit(tmp_path: Path) -> None:
    import asyncio

    client = _make_client(tmp_path)

    class DummyPage:
        pass

    async def fail_wait_and_get_response(*args, **kwargs):
        raise AssertionError("non-attachment submits must not use attachment fallback")

    client._wait_and_get_response = fail_wait_and_get_response

    result = asyncio.run(client._try_promote_attachment_visible_answer_after_unconfirmed_submit(
        DummyPage(),
        upload_paths=[],
        response_context={},
        submit_evidence={"submit_confirmed": False},
        phase_timings={},
        operation_started=0.0,
    ))

    assert result is None
