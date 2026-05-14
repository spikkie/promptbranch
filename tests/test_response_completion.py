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
