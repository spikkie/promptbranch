from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

import pytest

from promptbranch_browser_auth.client import ChatGPTBrowserClient
from promptbranch_browser_auth.config import ChatGPTBrowserConfig
from promptbranch_browser_auth.exceptions import ResponseTimeoutError, UnsupportedOperationError


class _FakePage:
    def __init__(self, labels: list[str]):
        self._labels = labels

    async def evaluate(self, script, roots):
        return list(self._labels)


@pytest.fixture()
def browser_client(tmp_path: Path) -> ChatGPTBrowserClient:
    config = ChatGPTBrowserConfig(
        project_url="https://chatgpt.com/",
        profile_dir=str(tmp_path / "profile"),
        debug=False,
    )
    return ChatGPTBrowserClient(config)


def test_project_source_capability_summary_maps_visible_labels(browser_client: ChatGPTBrowserClient) -> None:
    summary = browser_client._project_source_capability_summary(
        ["Upload", "Text input", "Google Drive", "Slack", "Upload"]
    )
    assert summary == [
        {"kind": "file", "label": "Upload"},
        {"kind": "text", "label": "Text input"},
        {"kind": "gdrive", "label": "Google Drive"},
        {"kind": "slack", "label": "Slack"},
    ]


def test_require_project_source_capability_raises_for_missing_link(browser_client: ChatGPTBrowserClient) -> None:
    page = _FakePage(["Upload", "Text input", "Google Drive", "Slack"])

    with pytest.raises(UnsupportedOperationError) as exc_info:
        asyncio.run(browser_client._require_project_source_capability(page, "link"))

    message = str(exc_info.value)
    assert "Project source kind 'link' is not exposed" in message
    assert "available_source_kinds=['file', 'text', 'gdrive', 'slack']" in message


def test_normalize_source_lookup_inputs_deduplicates(browser_client: ChatGPTBrowserClient) -> None:
    assert browser_client._normalize_source_lookup_inputs([" pasted.txt Document ", "pasted.txt Document", ""]) == [
        "pasted.txt Document"
    ]


def test_project_sources_url_sets_tab_query(browser_client: ChatGPTBrowserClient) -> None:
    assert browser_client._project_sources_url("https://chatgpt.com/g/g-p-123/project") == (
        "https://chatgpt.com/g/g-p-123/project?tab=sources"
    )
    assert browser_client._project_sources_url("https://chatgpt.com/g/g-p-123/project?foo=1&tab=chats") == (
        "https://chatgpt.com/g/g-p-123/project?foo=1&tab=sources"
    )




def test_project_source_persistence_refresh_skips_conversation_history_cooldown(browser_client: ChatGPTBrowserClient) -> None:
    page = _PersistenceRetryPage()
    calls: list[tuple[str, object]] = []
    attempts = {"count": 0}

    async def fake_goto(
        target_page,
        url: str,
        *,
        label: str,
        respect_history_rate_limit_cooldown: bool = True,
    ) -> None:
        calls.append(("goto", target_page, url, label, respect_history_rate_limit_cooldown))

    async def fake_wait_for_source_presence(target_page, **kwargs):
        attempts["count"] += 1
        calls.append(("wait", target_page, kwargs, attempts["count"]))
        if attempts["count"] == 1:
            raise ResponseTimeoutError("Timed out waiting for project source to appear: platform-gitops_0.0.4.zip")
        return {"identity": "platform-gitops_0.0.4.zip Document"}

    async def fake_empty_state_visible(_page) -> bool:
        return False

    async def fake_snapshot_project_source_cards(_page):
        return []

    async def fake_safe_page_url(_page) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    async def fake_capture_diagnostics(*_args, **_kwargs) -> None:
        return None

    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fake_wait_for_source_presence  # type: ignore[method-assign]
    browser_client._project_sources_empty_state_visible = fake_empty_state_visible  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot_project_source_cards  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._capture_project_source_persistence_diagnostics = fake_capture_diagnostics  # type: ignore[method-assign]

    persisted = asyncio.run(
        browser_client._verify_project_source_persistence(
            page,
            project_url="https://chatgpt.com/g/g-p-123/project",
            source_match_candidates=["platform-gitops_0.0.4.zip"],
            retry_backoff_ms=(25,),
        )
    )

    assert persisted == {
        "identity": "platform-gitops_0.0.4.zip Document",
        "_promptbranch_verification_mode": "post_refresh",
        "_promptbranch_ui_card_seen_before_refresh": False,
        "_promptbranch_post_refresh_attempt": 1,
    }
    assert (
        "goto",
        page,
        "https://chatgpt.com/g/g-p-123/project?tab=sources",
        "project-source-add-persistence-refresh",
        False,
    ) in calls




def test_file_persistence_candidates_reject_unanchored_generic_metadata_card(browser_client: ChatGPTBrowserClient) -> None:
    candidates = browser_client._build_persistence_source_candidates(
        requested_match="chatgpt_claudecode_workflow-2_v0.1.54.zip",
        source_match_candidates=[
            "chatgpt_claudecode_workflow-2_v0.1.54.zip",
            "chatgpt_claudecode_workflow-2_v0.1.54.zip Document",
        ],
        matched_card={
            "title": "Sidebar ChatGPT",
            "subtitle": "File contents may not be accessible",
            "identity": "Sidebar ChatGPT File contents may not be accessible",
            "text": "Sidebar ChatGPT File contents may not be accessible",
        },
        source_kind="file",
    )

    assert candidates == [
        "chatgpt_claudecode_workflow-2_v0.1.54.zip",
        "chatgpt_claudecode_workflow-2_v0.1.54.zip Document",
    ]
    assert "Sidebar ChatGPT" not in candidates
    assert "File contents may not be accessible" not in candidates


def test_file_persistence_candidates_keep_filename_anchored_inaccessible_card(browser_client: ChatGPTBrowserClient) -> None:
    candidates = browser_client._build_persistence_source_candidates(
        requested_match="chatgpt_claudecode_workflow-2_v0.1.54.zip",
        source_match_candidates=[
            "chatgpt_claudecode_workflow-2_v0.1.54.zip",
            "chatgpt_claudecode_workflow-2_v0.1.54.zip Document",
        ],
        matched_card={
            "title": "chatgpt_claudecode_workflow-2_v0.1.54.zip",
            "subtitle": "File contents may not be accessible",
            "identity": "chatgpt_claudecode_workflow-2_v0.1.54.zip File contents may not be accessible",
            "text": "chatgpt_claudecode_workflow-2_v0.1.54.zip File contents may not be accessible",
        },
        source_kind="file",
    )

    assert "chatgpt_claudecode_workflow-2_v0.1.54.zip File contents may not be accessible" in candidates
    assert "File contents may not be accessible" not in candidates


def test_match_source_card_ignores_generic_metadata_only_candidate(browser_client: ChatGPTBrowserClient) -> None:
    matched = browser_client._match_source_card(
        [
            {
                "title": "Sidebar ChatGPT",
                "subtitle": "File contents may not be accessible",
                "identity": "Sidebar ChatGPT File contents may not be accessible",
                "text": "Sidebar ChatGPT File contents may not be accessible",
            }
        ],
        ["File contents may not be accessible"],
    )

    assert matched is None


def test_wait_for_source_presence_does_not_accept_wrong_single_card_with_candidates(
    browser_client: ChatGPTBrowserClient,
) -> None:
    class _SingleWrongCardPage:
        def __init__(self) -> None:
            self.wait_calls: list[int] = []

        async def wait_for_timeout(self, timeout_ms: int) -> None:
            self.wait_calls.append(timeout_ms)

    page = _SingleWrongCardPage()

    async def fake_snapshot(*_args, **_kwargs):
        return [
            {
                "title": "Sidebar ChatGPT",
                "subtitle": "File contents may not be accessible",
                "identity": "Sidebar ChatGPT File contents may not be accessible",
                "text": "Sidebar ChatGPT File contents may not be accessible",
            }
        ]

    async def fake_find_container(*_args, **_kwargs):
        return None

    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._find_project_source_container = fake_find_container  # type: ignore[method-assign]

    with pytest.raises(ResponseTimeoutError):
        asyncio.run(
            browser_client._wait_for_source_presence(
                page,
                source_match_candidates=["chatgpt_claudecode_workflow-2_v0.1.54.zip"],
                before_sources=[],
                accept_single_new_card=True,
                timeout_ms=1,
            )
        )


def test_build_source_match_candidates_for_file_includes_document_identity(browser_client: ChatGPTBrowserClient, tmp_path: Path) -> None:
    file_path = tmp_path / "release.zip"
    candidates = browser_client._build_source_match_candidates(
        "file",
        value=None,
        display_name=None,
        file_path=str(file_path),
    )

    assert candidates == ["release.zip", "release.zip Document"]


def test_find_existing_file_source_for_overwrite_matches_document_card_identity(browser_client: ChatGPTBrowserClient) -> None:
    page = object()
    initial_sources = [
        {
            "identity": "release.zip Document",
            "title": "release.zip",
            "subtitle": "Document",
            "text": "release.zip\nDocument",
            "key": "release.zip",
        }
    ]

    async def fail_wait_for_source_presence(*_args, **_kwargs):
        raise AssertionError("initial snapshot should be sufficient")

    async def fail_verify_persistence(*_args, **_kwargs):
        raise AssertionError("initial snapshot should be sufficient")

    browser_client._wait_for_source_presence = fail_wait_for_source_presence  # type: ignore[method-assign]
    browser_client._verify_project_source_persistence = fail_verify_persistence  # type: ignore[method-assign]

    result = asyncio.run(
        browser_client._find_existing_file_source_for_overwrite(
            page,
            source_match_candidates=["release.zip", "release.zip Document"],
            initial_sources=initial_sources,
            project_url="https://chatgpt.com/g/g-p-123/project",
        )
    )

    assert result == initial_sources[0]

def test_build_persistence_source_candidates_prefers_rendered_identity(browser_client: ChatGPTBrowserClient) -> None:
    candidates = browser_client._build_persistence_source_candidates(
        requested_match="Integration note for run 123",
        source_match_candidates=["Integration note for run 123", "itest-text-123"],
        matched_card={
            "identity": "pasted.txt Document",
            "title": "pasted.txt",
            "subtitle": "Document",
            "text": "pasted.txt\nDocument",
        },
    )

    assert candidates == [
        "Integration note for run 123",
        "itest-text-123",
        "pasted.txt Document",
        "pasted.txt",
        "Document",
    ]


def test_verify_project_source_persistence_requires_refresh_after_current_surface_match(browser_client: ChatGPTBrowserClient) -> None:
    page = object()
    calls: list[tuple[str, object]] = []

    async def fake_goto(target_page, url: str, *, label: str, respect_history_rate_limit_cooldown: bool = True) -> None:
        calls.append(("goto", target_page, url, label, respect_history_rate_limit_cooldown))

    async def fake_wait_for_source_presence(target_page, **kwargs):
        calls.append(("wait", target_page, kwargs))
        return {"identity": "pasted.txt Document"}

    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fake_wait_for_source_presence  # type: ignore[method-assign]

    persisted = asyncio.run(
        browser_client._verify_project_source_persistence(
            page,
            project_url="https://chatgpt.com/g/g-p-123/project",
            source_match_candidates=["pasted.txt Document"],
        )
    )

    assert persisted == {
        "identity": "pasted.txt Document",
        "_promptbranch_verification_mode": "post_refresh",
        "_promptbranch_ui_card_seen_before_refresh": True,
        "_promptbranch_post_refresh_attempt": 1,
    }
    assert calls == [
        (
            "wait",
            page,
            {
                "source_match_candidates": ["pasted.txt Document"],
                "before_sources": None,
                "accept_single_new_card": False,
                "timeout_ms": 10_000,
            },
        ),
        (
            "goto",
            page,
            "https://chatgpt.com/g/g-p-123/project?tab=sources",
            "project-source-add-persistence-refresh",
            False,
        ),
        (
            "wait",
            page,
            {
                "source_match_candidates": ["pasted.txt Document"],
                "before_sources": None,
                "accept_single_new_card": False,
                "timeout_ms": 15_000,
            },
        ),
    ]


class _PersistenceRetryPage:
    def __init__(self) -> None:
        self.wait_calls: list[int] = []

    async def wait_for_timeout(self, timeout_ms: int) -> None:
        self.wait_calls.append(timeout_ms)
        await asyncio.sleep(0)


def test_verify_project_source_persistence_refreshes_after_pre_refresh_timeout(browser_client: ChatGPTBrowserClient) -> None:
    page = _PersistenceRetryPage()
    calls: list[tuple[str, object]] = []
    attempts = {"count": 0}

    async def fake_goto(target_page, url: str, *, label: str, respect_history_rate_limit_cooldown: bool = True) -> None:
        calls.append(("goto", target_page, url, label, respect_history_rate_limit_cooldown))

    async def fake_wait_for_source_presence(target_page, **kwargs):
        attempts["count"] += 1
        calls.append(("wait", target_page, kwargs, attempts["count"]))
        if attempts["count"] == 1:
            raise ResponseTimeoutError("Timed out waiting for project source to appear: pasted.txt Document")
        return {"identity": "pasted.txt Document"}

    async def fake_empty_state_visible(_page) -> bool:
        return True

    async def fake_snapshot_project_source_cards(_page):
        return []

    async def fake_safe_page_url(_page) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    async def fake_write_json(_path, _payload) -> None:
        return None

    async def fake_write_text(_path, _text) -> None:
        return None

    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fake_wait_for_source_presence  # type: ignore[method-assign]
    browser_client._project_sources_empty_state_visible = fake_empty_state_visible  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot_project_source_cards  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._write_json = fake_write_json  # type: ignore[method-assign]
    browser_client._write_text = fake_write_text  # type: ignore[method-assign]

    persisted = asyncio.run(
        browser_client._verify_project_source_persistence(
            page,
            project_url="https://chatgpt.com/g/g-p-123/project",
            source_match_candidates=["pasted.txt Document"],
            retry_backoff_ms=(25,),
        )
    )

    assert persisted == {
        "identity": "pasted.txt Document",
        "_promptbranch_verification_mode": "post_refresh",
        "_promptbranch_ui_card_seen_before_refresh": False,
        "_promptbranch_post_refresh_attempt": 1,
    }
    assert calls[0][0] == "wait"
    assert calls[0][3] == 1
    assert calls[1] == (
        "goto",
        page,
        "https://chatgpt.com/g/g-p-123/project?tab=sources",
        "project-source-add-persistence-refresh",
        False,
    )
    assert calls[2][0] == "wait"
    assert calls[2][3] == 2
    assert page.wait_calls == []


def test_build_persistence_source_candidates_omits_legacy_pasted_text_fallback(browser_client: ChatGPTBrowserClient) -> None:
    candidates = browser_client._build_persistence_source_candidates(
        requested_match="Integration note for run 123",
        source_match_candidates=["Integration note for run 123", "itest-text-123"],
        matched_card=None,
        source_kind="text",
        before_sources=[],
    )

    assert candidates == [
        "Integration note for run 123",
        "itest-text-123",
    ]
    assert "pasted.txt Document" not in candidates
    assert "pasted.txt" not in candidates


def test_build_persistence_source_candidates_does_not_match_old_generic_text_source(browser_client: ChatGPTBrowserClient) -> None:
    candidates = browser_client._build_persistence_source_candidates(
        requested_match="Integration note for run 123",
        source_match_candidates=["Integration note for run 123", "itest-text-123"],
        matched_card=None,
        source_kind="text",
        before_sources=[{"identity": "pasted.txt Document", "title": "pasted.txt", "text": "pasted.txt Document"}],
    )

    assert "pasted.txt Document" not in candidates
    assert "pasted.txt" not in candidates


def test_add_project_source_operation_defers_text_presence_timeout_to_persistence(browser_client: ChatGPTBrowserClient) -> None:
    page = object()
    call_order: list[str] = []

    async def fake_ensure_logged_in(*_args, **_kwargs) -> None:
        return None

    async def fake_goto(*_args, **_kwargs) -> None:
        return None

    async def fake_open_sources_tab(*_args, **_kwargs) -> None:
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return []

    async def fake_add_textual_source(*_args, **_kwargs) -> None:
        return None

    async def fake_wait_for_source_presence(*_args, **_kwargs):
        call_order.append("initial_presence_timeout")
        raise ResponseTimeoutError("Timed out waiting for project source to appear: Integration note for run 123")

    async def fake_wait_for_post_save_settle(*_args, **kwargs):
        call_order.append("settle")
        assert kwargs["source_kind"] == "text"
        return {"dialog_visible": False, "add_button_visible": True, "source_card_count": 0, "empty_state_visible": True}

    async def fake_wait_for_save_quiet(*_args, **kwargs):
        call_order.append("save_quiet")
        assert kwargs["source_kind"] == "text"
        return {"saw_relevant": True, "saw_commit": True, "started": 2, "finished": 1, "failed": 0, "inflight": 1}

    async def fake_verify_persistence(*_args, **kwargs):
        call_order.append("verify")
        assert kwargs["source_match_candidates"] == [
            "Integration note for run 123",
            "itest-text-123",
        ]
        return {"identity": "Integration note for run 123.txt Document", "title": "Integration note for run 123.txt", "text": "Integration note for run 123.txt Document"}

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_open_sources_tab  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._add_project_textual_source = fake_add_textual_source  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fake_wait_for_source_presence  # type: ignore[method-assign]
    browser_client._wait_for_project_source_post_save_settle = fake_wait_for_post_save_settle  # type: ignore[method-assign]
    browser_client._wait_for_project_source_save_request_quiet = fake_wait_for_save_quiet  # type: ignore[method-assign]
    browser_client._verify_project_source_persistence = fake_verify_persistence  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._install_project_source_save_request_watch = lambda *_args, **_kwargs: {"installed": True}  # type: ignore[method-assign]
    browser_client._dispose_project_source_save_request_watch = lambda *_args, **_kwargs: None  # type: ignore[method-assign]

    result = asyncio.run(
        browser_client._add_project_source_operation(
            context=None,
            page=page,
            source_kind="text",
            value="Integration note for run 123",
            file_path=None,
            display_name="itest-text-123",
            keep_open=False,
        )
    )

    assert call_order == ["initial_presence_timeout", "settle", "save_quiet", "verify"]
    assert result["ok"] is True
    assert result["source_match"] == "Integration note for run 123.txt Document"
    assert result["persistence_verified"] is True


def test_add_project_source_operation_requires_post_refresh_persistence(browser_client: ChatGPTBrowserClient) -> None:
    page = object()
    call_order: list[str] = []

    async def fake_ensure_logged_in(*_args, **_kwargs) -> None:
        return None

    async def fake_goto(*_args, **_kwargs) -> None:
        return None

    async def fake_open_sources_tab(*_args, **_kwargs) -> None:
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return []

    async def fake_add_textual_source(*_args, **_kwargs) -> None:
        return None

    async def fake_wait_for_source_presence(*_args, **_kwargs):
        call_order.append("presence")
        return {
            "identity": "pasted.txt Document",
            "title": "pasted.txt",
            "subtitle": "Document",
            "text": "pasted.txt\nDocument",
        }

    async def fake_wait_for_post_save_settle(*_args, **kwargs):
        call_order.append("settle")
        assert kwargs["source_kind"] == "text"
        return {
            "dialog_visible": False,
            "add_button_visible": True,
            "source_card_count": 1,
            "empty_state_visible": False,
            "url_stable": True,
            "current_url": "https://chatgpt.com/g/g-p-123/project?tab=sources",
        }

    async def fake_wait_for_save_quiet(*_args, **kwargs):
        call_order.append("save_quiet")
        assert kwargs["source_kind"] == "text"
        return {
            "saw_relevant": True,
            "started": 1,
            "finished": 1,
            "failed": 0,
            "inflight": 0,
        }

    async def fake_verify_persistence(*_args, **kwargs):
        call_order.append("verify")
        assert kwargs["source_match_candidates"] == [
            "Integration note for run 123",
            "itest-text-123",
            "pasted.txt Document",
            "pasted.txt",
            "Document",
        ]
        return {
            "identity": "pasted.txt Document",
            "title": "pasted.txt",
            "subtitle": "Document",
            "text": "pasted.txt\nDocument",
        }

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_open_sources_tab  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._add_project_textual_source = fake_add_textual_source  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fake_wait_for_source_presence  # type: ignore[method-assign]
    browser_client._wait_for_project_source_post_save_settle = fake_wait_for_post_save_settle  # type: ignore[method-assign]
    browser_client._wait_for_project_source_save_request_quiet = fake_wait_for_save_quiet  # type: ignore[method-assign]
    browser_client._verify_project_source_persistence = fake_verify_persistence  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._install_project_source_save_request_watch = lambda *_args, **_kwargs: {"installed": False}  # type: ignore[method-assign]
    browser_client._dispose_project_source_save_request_watch = lambda *_args, **_kwargs: None  # type: ignore[method-assign]

    result = asyncio.run(
        browser_client._add_project_source_operation(
            context=None,
            page=page,
            source_kind="text",
            value="Integration note for run 123",
            file_path=None,
            display_name="itest-text-123",
            keep_open=False,
        )
    )

    assert call_order == ["presence", "settle", "save_quiet", "verify"]
    assert result["ok"] is True
    assert result["source_match"] == "pasted.txt Document"
    assert result["source_match_requested"] == "Integration note for run 123"
    assert result["persistence_verified"] is True


def test_wait_for_project_source_save_request_quiet_requires_relevant_requests_to_finish(browser_client: ChatGPTBrowserClient) -> None:
    class _QuietPage:
        def __init__(self) -> None:
            self.wait_calls: list[int] = []

        async def wait_for_timeout(self, timeout_ms: int) -> None:
            self.wait_calls.append(timeout_ms)
            await asyncio.sleep(0)

    page = _QuietPage()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        watch = {
            "installed": True,
            "source_kind": "text",
            "started": 1,
            "finished": 0,
            "failed": 0,
            "saw_relevant": True,
            "saw_commit": True,
            "inflight": {1},
            "last_activity": loop.time(),
        }

        async def advance_state() -> None:
            await asyncio.sleep(0)
            watch["inflight"].clear()
            watch["finished"] = 1
            watch["last_activity"] = loop.time() - 2

        loop.create_task(advance_state())
        settled = loop.run_until_complete(
            browser_client._wait_for_project_source_save_request_quiet(
                page,
                watch,
                source_kind="text",
                timeout_ms=1000,
                observation_window_ms=200,
                quiet_window_ms=100,
                poll_interval_ms=10,
            )
        )
    finally:
        asyncio.set_event_loop(None)
        loop.close()

    assert settled["saw_relevant"] is True
    assert settled["finished"] == 1
    assert settled["inflight"] == 0
    assert page.wait_calls




def test_wait_for_project_source_save_request_quiet_rejects_committed_stale_inflight(browser_client: ChatGPTBrowserClient) -> None:
    class _QuietPage:
        def __init__(self) -> None:
            self.wait_calls: list[int] = []

        async def wait_for_timeout(self, timeout_ms: int) -> None:
            self.wait_calls.append(timeout_ms)
            await asyncio.sleep(0)

    page = _QuietPage()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        now = loop.time()
        watch = {
            "installed": True,
            "source_kind": "text",
            "started": 2,
            "finished": 1,
            "failed": 0,
            "saw_relevant": True,
            "saw_commit": True,
            "commit_seen_at": now - 1.0,
            "inflight": {1},
            "last_activity": now - 1.0,
        }

        with pytest.raises(ResponseTimeoutError) as excinfo:
            loop.run_until_complete(
                browser_client._wait_for_project_source_save_request_quiet(
                    page,
                    watch,
                    source_kind="text",
                    timeout_ms=120,
                    observation_window_ms=40,
                    quiet_window_ms=20,
                    stale_inflight_after_commit_grace_ms=30,
                    poll_interval_ms=10,
                )
            )
    finally:
        asyncio.set_event_loop(None)
        loop.close()

    message = str(excinfo.value)
    assert "inflight=1" in message
    assert "stale_inflight_after_commit=True" in message
    assert "quiet_reason=stale_inflight_after_commit_not_quiet" in message



def test_wait_for_project_source_save_request_quiet_allows_stale_inflight_when_persistence_will_verify(browser_client: ChatGPTBrowserClient) -> None:
    class _QuietPage:
        def __init__(self) -> None:
            self.wait_calls: list[int] = []

        async def wait_for_timeout(self, timeout_ms: int) -> None:
            self.wait_calls.append(timeout_ms)
            await asyncio.sleep(0)

    page = _QuietPage()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        now = loop.time()
        watch = {
            "installed": True,
            "source_kind": "text",
            "started": 2,
            "finished": 1,
            "failed": 0,
            "saw_relevant": True,
            "saw_commit": True,
            "commit_seen_at": now - 1.0,
            "inflight": {1},
            "last_activity": now - 1.0,
        }

        result = loop.run_until_complete(
            browser_client._wait_for_project_source_save_request_quiet(
                page,
                watch,
                source_kind="text",
                timeout_ms=120,
                observation_window_ms=40,
                quiet_window_ms=20,
                stale_inflight_after_commit_grace_ms=30,
                poll_interval_ms=10,
                allow_stale_inflight_after_commit=True,
            )
        )
    finally:
        asyncio.set_event_loop(None)
        loop.close()

    assert result["quiet_now"] is True
    assert result["stale_inflight_after_commit"] is True
    assert result["stale_inflight_soft_quiet"] is True
    assert result["quiet_reason"] == "stale_inflight_after_commit_soft_quiet_requires_persistence_verification"

def test_wait_for_project_source_save_request_quiet_falls_back_to_observation_window(browser_client: ChatGPTBrowserClient) -> None:
    class _QuietPage:
        def __init__(self) -> None:
            self.wait_calls: list[int] = []

        async def wait_for_timeout(self, timeout_ms: int) -> None:
            self.wait_calls.append(timeout_ms)
            await asyncio.sleep(0)

    page = _QuietPage()
    watch = {
        "installed": True,
        "source_kind": "text",
        "started": 0,
        "finished": 0,
        "failed": 0,
        "saw_relevant": False,
        "saw_commit": False,
        "inflight": set(),
        "last_activity": None,
    }

    settled = asyncio.run(
        browser_client._wait_for_project_source_save_request_quiet(
            page,
            watch,
            source_kind="text",
            timeout_ms=500,
            observation_window_ms=50,
            quiet_window_ms=100,
            poll_interval_ms=10,
        )
    )

    assert settled["saw_relevant"] is False
    assert settled["observation_window_elapsed"] is True
    assert settled["quiet_now"] is True
    assert page.wait_calls


def test_is_project_source_save_request_matches_late_processing_commit(browser_client: ChatGPTBrowserClient) -> None:
    assert browser_client._is_project_source_save_request(
        "https://chatgpt.com/backend-api/files/process_upload_stream",
        source_kind="text",
    ) is True
    assert browser_client._is_project_source_commit_request(
        "https://chatgpt.com/backend-api/files/process_upload_stream",
        source_kind="text",
    ) is True


def test_wait_for_project_source_save_request_quiet_waits_for_late_commit_window(browser_client: ChatGPTBrowserClient) -> None:
    class _QuietPage:
        def __init__(self) -> None:
            self.wait_calls: list[int] = []

        async def wait_for_timeout(self, timeout_ms: int) -> None:
            self.wait_calls.append(timeout_ms)
            await asyncio.sleep(0)

    page = _QuietPage()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        watch = {
            "installed": True,
            "source_kind": "text",
            "started": 1,
            "finished": 1,
            "failed": 0,
            "saw_relevant": True,
            "saw_commit": False,
            "inflight": set(),
            "last_activity": loop.time() - 1,
        }

        async def advance_state() -> None:
            await asyncio.sleep(0)
            watch["saw_commit"] = True
            watch["started"] = 2
            watch["finished"] = 2
            watch["last_activity"] = loop.time() - 1

        loop.create_task(advance_state())
        settled = loop.run_until_complete(
            browser_client._wait_for_project_source_save_request_quiet(
                page,
                watch,
                source_kind="text",
                timeout_ms=1000,
                observation_window_ms=200,
                quiet_window_ms=50,
                poll_interval_ms=10,
            )
        )
    finally:
        asyncio.set_event_loop(None)
        loop.close()

    assert settled["saw_relevant"] is True
    assert settled["saw_commit"] is True
    assert settled["started"] == 2
    assert settled["finished"] == 2
    assert page.wait_calls


def test_wait_for_project_source_post_save_settle_requires_stable_closed_dialog(browser_client: ChatGPTBrowserClient) -> None:
    class _SettlingPage:
        def __init__(self) -> None:
            self.wait_calls: list[int] = []

        async def wait_for_timeout(self, timeout_ms: int) -> None:
            self.wait_calls.append(timeout_ms)

    page = _SettlingPage()
    states = iter(
        [
            {"dialog_visible": True, "add_button_visible": False, "source_cards": [], "empty_state_visible": False, "url": "https://chatgpt.com/g/g-p-123/project?tab=sources"},
            {"dialog_visible": False, "add_button_visible": True, "source_cards": [{"identity": "pasted.txt Document"}], "empty_state_visible": False, "url": "https://chatgpt.com/g/g-p-123/project?tab=sources"},
            {"dialog_visible": False, "add_button_visible": True, "source_cards": [{"identity": "pasted.txt Document"}], "empty_state_visible": False, "url": "https://chatgpt.com/g/g-p-123/project?tab=sources"},
            {"dialog_visible": False, "add_button_visible": True, "source_cards": [{"identity": "pasted.txt Document"}], "empty_state_visible": False, "url": "https://chatgpt.com/g/g-p-123/project?tab=sources"},
        ]
    )
    current_state = {"dialog_visible": True, "add_button_visible": False, "source_cards": [], "empty_state_visible": False, "url": "https://chatgpt.com/g/g-p-123/project?tab=sources"}

    async def fake_find_visible_locator(*_args, label: str, **_kwargs):
        nonlocal current_state
        if "post-save-dialog" in label:
            current_state = next(states)
            return object() if current_state["dialog_visible"] else None
        if "post-save-add-button" in label:
            return object() if current_state["add_button_visible"] else None
        raise AssertionError(f"unexpected label: {label}")

    async def fake_snapshot(*_args, **_kwargs):
        return current_state["source_cards"]

    async def fake_empty_state(*_args, **_kwargs):
        return current_state["empty_state_visible"]

    async def fake_safe_page_url(*_args, **_kwargs):
        return current_state["url"]

    browser_client._find_visible_locator = fake_find_visible_locator  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._project_sources_empty_state_visible = fake_empty_state  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]

    settled = asyncio.run(
        browser_client._wait_for_project_source_post_save_settle(
            page,
            source_kind="text",
            poll_interval_ms=10,
            required_observations=3,
        )
    )

    assert settled["dialog_visible"] is False
    assert settled["add_button_visible"] is True
    assert settled["source_card_count"] == 1
    assert settled["url_stable"] is True
    assert page.wait_calls == [10, 10, 10]




def test_clear_profile_singleton_locks_removes_artifacts(tmp_path: Path) -> None:
    profile_dir = tmp_path / "profile"
    profile_dir.mkdir()
    for name in ("SingletonLock", "SingletonSocket", "SingletonCookie"):
        (profile_dir / name).write_text("x", encoding="utf-8")

    config = ChatGPTBrowserConfig(
        project_url="https://chatgpt.com/",
        email="user@example.com",
        password="secret",
        profile_dir=str(profile_dir),
        clear_singleton_locks=True,
    )
    client = ChatGPTBrowserClient(config)

    removed = client._clear_profile_singleton_locks()

    assert removed == ["SingletonLock", "SingletonSocket", "SingletonCookie"]
    for name in ("SingletonLock", "SingletonSocket", "SingletonCookie"):
        assert not (profile_dir / name).exists()


def test_build_source_match_candidates_for_file_uses_basename(browser_client: ChatGPTBrowserClient) -> None:
    candidates = browser_client._build_source_match_candidates(
        "file",
        value=None,
        display_name="/tmp/releases/candlecast-src-0.19.5.82.2.zip",
        file_path="/var/tmp/uploads/candlecast-src-0.19.5.82.2.zip",
    )

    assert candidates == ["candlecast-src-0.19.5.82.2.zip", "candlecast-src-0.19.5.82.2.zip Document"]



def test_wait_for_project_source_post_save_settle_accepts_restored_surface_with_stale_dialog(browser_client: ChatGPTBrowserClient) -> None:
    class _SettlingPage:
        def __init__(self) -> None:
            self.wait_calls: list[int] = []

        async def wait_for_timeout(self, timeout_ms: int) -> None:
            self.wait_calls.append(timeout_ms)

    page = _SettlingPage()
    current_state = {
        "dialog_visible": True,
        "add_button_visible": True,
        "source_cards": [
            {"identity": "existing.txt Document"},
            {"identity": "replacement.txt Document"},
        ],
        "empty_state_visible": False,
        "url": "https://chatgpt.com/g/g-p-123/project?tab=sources",
    }

    async def fake_find_visible_locator(*_args, label: str, **_kwargs):
        if "post-save-dialog" in label:
            return object() if current_state["dialog_visible"] else None
        if "post-save-add-button" in label:
            return object() if current_state["add_button_visible"] else None
        raise AssertionError(f"unexpected label: {label}")

    async def fake_snapshot(*_args, **_kwargs):
        return current_state["source_cards"]

    async def fake_empty_state(*_args, **_kwargs):
        return current_state["empty_state_visible"]

    async def fake_safe_page_url(*_args, **_kwargs):
        return current_state["url"]

    async def fake_duplicate_notice(*_args, **_kwargs):
        return None

    browser_client._find_visible_locator = fake_find_visible_locator  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._project_sources_empty_state_visible = fake_empty_state  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._find_project_source_duplicate_notice = fake_duplicate_notice  # type: ignore[method-assign]

    settled = asyncio.run(
        browser_client._wait_for_project_source_post_save_settle(
            page,
            source_kind="file",
            poll_interval_ms=10,
            required_observations=2,
        )
    )

    assert settled["dialog_visible"] is True
    assert settled["dialog_soft_closed"] is True
    assert settled["dialog_false_positive_possible"] is True
    assert settled["add_button_visible"] is True
    assert settled["source_card_count"] == 2
    assert settled["url_stable"] is True
    assert page.wait_calls == [10, 10]

def test_wait_for_project_source_post_save_settle_stops_on_duplicate_notice(browser_client: ChatGPTBrowserClient) -> None:
    class _DuplicatePage:
        def __init__(self) -> None:
            self.wait_calls: list[int] = []

        async def wait_for_timeout(self, timeout_ms: int) -> None:
            self.wait_calls.append(timeout_ms)
            await asyncio.sleep(0)

    page = _DuplicatePage()

    async def fake_find_visible_locator(*_args, **_kwargs):
        return object()

    async def fake_snapshot(*_args, **_kwargs):
        return [{"title": "candlecast-src-0.19.5.82.2.zip"}]

    async def fake_empty_state(*_args, **_kwargs):
        return False

    async def fake_safe_page_url(*_args, **_kwargs):
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    async def fake_duplicate_notice(*_args, **_kwargs):
        return "candlecast-src-0.19.5.82.2.zip already exists"

    browser_client._find_visible_locator = fake_find_visible_locator  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._project_sources_empty_state_visible = fake_empty_state  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._find_project_source_duplicate_notice = fake_duplicate_notice  # type: ignore[method-assign]

    with pytest.raises(Exception) as exc_info:
        asyncio.run(
            browser_client._wait_for_project_source_post_save_settle(
                page,
                source_kind="file",
                expected_source_name="candlecast-src-0.19.5.82.2.zip",
                timeout_ms=500,
                poll_interval_ms=10,
                required_observations=2,
            )
        )

    assert "already exists" in str(exc_info.value)


def test_add_project_source_operation_short_circuits_existing_duplicate_file(browser_client: ChatGPTBrowserClient, tmp_path: Path) -> None:
    page = object()

    async def fake_ensure_logged_in(*_args, **_kwargs) -> None:
        return None

    async def fake_goto(*_args, **_kwargs) -> None:
        return None

    async def fake_open_sources_tab(*_args, **_kwargs) -> None:
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return [{
            "identity": "candlecast-src-0.16.5.16.zip",
            "title": "candlecast-src-0.16.5.16.zip",
            "text": "candlecast-src-0.16.5.16.zip File contents may not be accessible",
        }]

    async def fail_add_file_source(*_args, **_kwargs) -> None:
        raise AssertionError("duplicate file add should short-circuit before opening upload flow")

    async def fake_verify_persistence(*_args, **kwargs):
        candidates = kwargs["source_match_candidates"]
        assert candidates[0] == "candlecast-src-0.16.5.16.zip"
        assert "candlecast-src-0.16.5.16.zip File contents may not be accessible" in candidates
        return {
            "identity": "candlecast-src-0.16.5.16.zip",
            "title": "candlecast-src-0.16.5.16.zip",
            "text": "candlecast-src-0.16.5.16.zip File contents may not be accessible",
        }

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_open_sources_tab  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._add_project_file_source = fail_add_file_source  # type: ignore[method-assign]
    browser_client._verify_project_source_persistence = fake_verify_persistence  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]

    file_path = str(tmp_path / "candlecast-src-0.16.5.16.zip")
    Path(file_path).write_bytes(b"zip")
    result = asyncio.run(
        browser_client._add_project_source_operation(
            context=None,
            page=page,
            source_kind="file",
            value=None,
            file_path=file_path,
            display_name=file_path,
            keep_open=False,
            overwrite_existing=False,
        )
    )

    assert result["ok"] is True
    assert result["already_exists"] is True
    assert result["added"] is False
    assert result["source_match_requested"] == "candlecast-src-0.16.5.16.zip"
    assert "already exists" in result["duplicate_notice"].lower()




def test_add_project_source_operation_uses_empty_snapshot_fast_path_for_new_file(browser_client: ChatGPTBrowserClient, tmp_path: Path) -> None:
    page = object()
    calls: dict[str, object] = {
        "added": False,
        "presence_calls": 0,
        "pre_upload_presence_calls": 0,
        "removed": False,
        "preflight_verify_calls": 0,
    }

    async def fake_ensure_logged_in(*_args, **_kwargs) -> None:
        return None

    async def fake_goto(*_args, **_kwargs) -> None:
        return None

    async def fake_open_sources_tab(*_args, **_kwargs) -> None:
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return []

    async def fake_empty_state(*_args, **_kwargs) -> bool:
        return True

    async def fake_wait_for_source_presence(*_args, **_kwargs):
        calls["presence_calls"] = int(calls["presence_calls"]) + 1
        if not calls["added"]:
            calls["pre_upload_presence_calls"] = int(calls["pre_upload_presence_calls"]) + 1
            raise AssertionError("empty initial snapshot must not run overwrite absence preflight")
        return {
            "identity": "itest-file.txt Document",
            "title": "itest-file.txt Document",
            "text": "itest-file.txt Document · Jun 10, 2026",
        }

    async def fake_remove(*_args, **_kwargs):
        calls["removed"] = True
        raise AssertionError("new-file fast path must not remove any source")

    async def fake_add_file_source(*_args, **_kwargs) -> None:
        calls["added"] = True

    async def fake_wait_for_post_save_settle(*_args, **_kwargs):
        return None

    async def fake_wait_for_quiet(*_args, **_kwargs):
        return None

    async def fake_verify_persistence(*_args, **_kwargs):
        if not calls["added"]:
            calls["preflight_verify_calls"] = int(calls["preflight_verify_calls"]) + 1
            raise AssertionError("empty initial snapshot must not run refreshed overwrite preflight")
        return {
            "identity": "itest-file.txt Document",
            "title": "itest-file.txt Document",
            "text": "itest-file.txt Document · Jun 10, 2026",
        }

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_open_sources_tab  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._project_sources_empty_state_visible = fake_empty_state  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fake_wait_for_source_presence  # type: ignore[method-assign]
    browser_client._verify_project_source_persistence = fake_verify_persistence  # type: ignore[method-assign]
    browser_client._remove_project_source_operation = fake_remove  # type: ignore[method-assign]
    browser_client._add_project_file_source = fake_add_file_source  # type: ignore[method-assign]
    browser_client._wait_for_project_source_post_save_settle = fake_wait_for_post_save_settle  # type: ignore[method-assign]
    browser_client._wait_for_project_source_save_request_quiet = fake_wait_for_quiet  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._install_project_source_save_request_watch = lambda *_args, **_kwargs: {"installed": False}  # type: ignore[method-assign]
    browser_client._dispose_project_source_save_request_watch = lambda *_args, **_kwargs: None  # type: ignore[method-assign]

    file_path = tmp_path / "itest-file.txt"
    file_path.write_bytes(b"first")
    result = asyncio.run(
        browser_client._add_project_source_operation(
            context=None,
            page=page,
            source_kind="file",
            value=None,
            file_path=str(file_path),
            display_name=str(file_path),
            keep_open=False,
        )
    )

    assert calls["added"] is True
    assert calls["removed"] is False
    assert calls["pre_upload_presence_calls"] == 0
    assert calls["preflight_verify_calls"] == 0
    assert result["ok"] is True
    assert result["already_exists"] is False
    assert result["overwritten"] is False
    assert result["removed_existing"] is False


def test_add_project_source_operation_overwrite_uses_clean_title_and_retries_anchor_lookup(browser_client: ChatGPTBrowserClient, tmp_path: Path) -> None:
    page = object()
    calls: dict[str, object] = {"remove_attempts": [], "added": False}

    async def fake_ensure_logged_in(*_args, **_kwargs) -> None:
        return None

    async def fake_goto(*_args, **_kwargs) -> None:
        return None

    async def fake_open_sources_tab(*_args, **_kwargs) -> None:
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return [{
            "identity": "architecture-process_0.1.29.zip File contents may not be accessible",
            "title": "architecture-process_0.1.29.zip",
            "text": "architecture-process_0.1.29.zip File contents may not be accessible",
        }]

    async def fake_remove(*_args, **kwargs):
        calls["remove_attempts"].append({"source_name": kwargs["source_name"], "exact": kwargs["exact"]})
        assert kwargs["source_name"] == "architecture-process_0.1.29.zip"
        if kwargs["exact"] is True:
            raise ResponseTimeoutError("Could not find the remove/delete action for the selected project source")
        return {"ok": True, "removed_via_ui": True, "source_match": "architecture-process_0.1.29.zip"}

    async def fake_add_file_source(*_args, **_kwargs) -> None:
        calls["added"] = True

    async def fake_wait_for_source_presence(*_args, **_kwargs):
        return {"identity": "architecture-process_0.1.29.zip", "title": "architecture-process_0.1.29.zip", "text": "architecture-process_0.1.29.zip"}

    async def fake_wait_for_post_save_settle(*_args, **_kwargs):
        return None

    async def fake_wait_for_quiet(*_args, **_kwargs):
        return None

    async def fake_verify_persistence(*_args, **_kwargs):
        return {"identity": "architecture-process_0.1.29.zip", "title": "architecture-process_0.1.29.zip", "text": "architecture-process_0.1.29.zip"}

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_open_sources_tab  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._remove_project_source_operation = fake_remove  # type: ignore[method-assign]
    browser_client._add_project_file_source = fake_add_file_source  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fake_wait_for_source_presence  # type: ignore[method-assign]
    browser_client._wait_for_project_source_post_save_settle = fake_wait_for_post_save_settle  # type: ignore[method-assign]
    browser_client._wait_for_project_source_save_request_quiet = fake_wait_for_quiet  # type: ignore[method-assign]
    browser_client._verify_project_source_persistence = fake_verify_persistence  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._install_project_source_save_request_watch = lambda *_args, **_kwargs: {"installed": False}  # type: ignore[method-assign]
    browser_client._dispose_project_source_save_request_watch = lambda *_args, **_kwargs: None  # type: ignore[method-assign]

    file_path = tmp_path / "architecture-process_0.1.29.zip"
    file_path.write_bytes(b"zip")
    result = asyncio.run(
        browser_client._add_project_source_operation(
            context=None,
            page=page,
            source_kind="file",
            value=None,
            file_path=str(file_path),
            display_name=str(file_path),
            keep_open=False,
        )
    )

    assert calls["remove_attempts"] == [
        {"source_name": "architecture-process_0.1.29.zip", "exact": True},
        {"source_name": "architecture-process_0.1.29.zip", "exact": False},
    ]
    assert calls["added"] is True
    assert result["ok"] is True
    assert result["overwritten"] is True
    assert result["removed_existing"] is True





def test_add_project_source_operation_skips_legacy_absence_probe_for_nonempty_family_miss(browser_client: ChatGPTBrowserClient, tmp_path: Path) -> None:
    page = object()
    calls: dict[str, object] = {
        "presence_calls": 0,
        "removed": False,
        "added": False,
    }

    async def fake_ensure_logged_in(*_args, **_kwargs) -> None:
        return None

    async def fake_goto(*_args, **_kwargs) -> None:
        return None

    async def fake_open_sources_tab(*_args, **_kwargs) -> None:
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return [{"identity": "other-file.txt", "title": "other-file.txt", "text": "other-file.txt"}]

    async def fail_wait_for_source_presence(*_args, **_kwargs):
        calls["presence_calls"] = int(calls["presence_calls"]) + 1
        raise AssertionError("file adds must not use the legacy exact-name absence/presence probe")

    async def fake_remove(*_args, **_kwargs):
        calls["removed"] = True
        raise AssertionError("a family miss must not remove any source")

    async def fake_add_file_source(*_args, **_kwargs) -> None:
        calls["added"] = True

    async def fake_wait_for_post_save_settle(*_args, **_kwargs):
        return None

    async def fake_wait_for_quiet(*_args, **_kwargs):
        return None

    async def fake_verify_persistence(*_args, **_kwargs):
        return {
            "identity": "itest-file.txt Document",
            "title": "itest-file.txt",
            "text": "itest-file.txt Document · Jun 10, 2026",
        }

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_open_sources_tab  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fail_wait_for_source_presence  # type: ignore[method-assign]
    browser_client._remove_project_source_operation = fake_remove  # type: ignore[method-assign]
    browser_client._add_project_file_source = fake_add_file_source  # type: ignore[method-assign]
    browser_client._wait_for_project_source_post_save_settle = fake_wait_for_post_save_settle  # type: ignore[method-assign]
    browser_client._wait_for_project_source_save_request_quiet = fake_wait_for_quiet  # type: ignore[method-assign]
    browser_client._verify_project_source_persistence = fake_verify_persistence  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._install_project_source_save_request_watch = lambda *_args, **_kwargs: {"installed": False}  # type: ignore[method-assign]
    browser_client._dispose_project_source_save_request_watch = lambda *_args, **_kwargs: None  # type: ignore[method-assign]

    file_path = tmp_path / "itest-file.txt"
    file_path.write_text("first", encoding="utf-8")
    result = asyncio.run(
        browser_client._add_project_source_operation(
            context=None,
            page=page,
            source_kind="file",
            value=None,
            file_path=str(file_path),
            display_name=str(file_path),
            keep_open=False,
        )
    )

    assert calls == {"presence_calls": 0, "removed": False, "added": True}
    assert result["ok"] is True
    assert result["pre_upload_family_source_count"] == 0
    assert result["source_family_regex"].startswith("^itest")

def test_add_project_source_operation_returns_structured_overwrite_failure(browser_client: ChatGPTBrowserClient, tmp_path: Path) -> None:
    page = object()

    async def fake_ensure_logged_in(*_args, **_kwargs) -> None:
        return None

    async def fake_goto(*_args, **_kwargs) -> None:
        return None

    async def fake_open_sources_tab(*_args, **_kwargs) -> None:
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return [{
            "identity": "architecture-process_0.1.29.zip File contents may not be accessible",
            "title": "architecture-process_0.1.29.zip",
            "text": "architecture-process_0.1.29.zip File contents may not be accessible",
        }]

    async def fake_remove(*_args, **_kwargs):
        raise ResponseTimeoutError("Could not find the remove/delete action for the selected project source")

    async def fail_add_file_source(*_args, **_kwargs) -> None:
        raise AssertionError("upload must not start when overwrite removal cannot be verified")

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_open_sources_tab  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._remove_project_source_operation = fake_remove  # type: ignore[method-assign]
    browser_client._add_project_file_source = fail_add_file_source  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]

    file_path = tmp_path / "architecture-process_0.1.29.zip"
    file_path.write_bytes(b"zip")
    result = asyncio.run(
        browser_client._add_project_source_operation(
            context=None,
            page=page,
            source_kind="file",
            value=None,
            file_path=str(file_path),
            display_name=str(file_path),
            keep_open=False,
        )
    )

    assert result["ok"] is False
    assert result["status"] == "overwrite_remove_failed"
    assert result["already_exists"] is True
    assert result["added"] is False
    assert result["operator_review_required"] is True
    assert result["overwrite_source_name"] == "architecture-process_0.1.29.zip"
    assert "remove/delete action" in result["overwrite_remove_error"]


def test_add_project_source_operation_reports_removed_existing_when_overwrite_persistence_fails(browser_client: ChatGPTBrowserClient, tmp_path: Path) -> None:
    page = object()
    calls: dict[str, object] = {"removed": False, "added": False}

    async def fake_ensure_logged_in(*_args, **_kwargs) -> None:
        return None

    async def fake_goto(*_args, **_kwargs) -> None:
        return None

    async def fake_open_sources_tab(*_args, **_kwargs) -> None:
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return [{"identity": "release.zip", "title": "release.zip", "text": "release.zip"}]

    async def fake_remove(*_args, **kwargs):
        calls["removed"] = True
        assert kwargs["source_name"] == "release.zip"
        return {"ok": True, "removed_via_ui": True, "source_match": "release.zip"}

    async def fake_add_file_source(*_args, **_kwargs) -> None:
        calls["added"] = True

    async def fake_wait_for_source_presence(*_args, **_kwargs):
        return {"identity": "release.zip", "title": "release.zip", "text": "release.zip"}

    async def fake_wait_for_post_save_settle(*_args, **_kwargs):
        return None

    async def fake_wait_for_quiet(*_args, **_kwargs):
        return None

    async def fake_verify_persistence(*_args, **_kwargs):
        raise ResponseTimeoutError("post-refresh verification did not find replacement release.zip")

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_open_sources_tab  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._remove_project_source_operation = fake_remove  # type: ignore[method-assign]
    browser_client._add_project_file_source = fake_add_file_source  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fake_wait_for_source_presence  # type: ignore[method-assign]
    browser_client._wait_for_project_source_post_save_settle = fake_wait_for_post_save_settle  # type: ignore[method-assign]
    browser_client._wait_for_project_source_save_request_quiet = fake_wait_for_quiet  # type: ignore[method-assign]
    browser_client._verify_project_source_persistence = fake_verify_persistence  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._install_project_source_save_request_watch = lambda *_args, **_kwargs: {"installed": True, "finished": 1, "failed": 0, "saw_commit": True, "inflight": set()}  # type: ignore[method-assign]
    browser_client._dispose_project_source_save_request_watch = lambda *_args, **_kwargs: None  # type: ignore[method-assign]

    file_path = tmp_path / "release.zip"
    file_path.write_bytes(b"zip")
    result = asyncio.run(
        browser_client._add_project_source_operation(
            context=None,
            page=page,
            source_kind="file",
            value=None,
            file_path=str(file_path),
            display_name=str(file_path),
            keep_open=False,
        )
    )

    assert calls["removed"] is True
    assert calls["added"] is True
    assert result["ok"] is False
    assert result["status"] == "overwrite_persistence_not_verified"
    assert result["overwritten"] is True
    assert result["removed_existing"] is True
    assert result["operator_review_required"] is True
    assert result["persistence_false_negative_possible"] is True
    assert "pb src list --json" in result["recovery_guidance"][0]
    assert "post-refresh verification" in result["persistence_error"]


def test_add_project_source_operation_returns_persistence_false_negative_diagnostics(browser_client: ChatGPTBrowserClient, tmp_path: Path) -> None:
    page = object()
    calls: dict[str, object] = {"added": False}

    async def fake_ensure_logged_in(*_args, **_kwargs) -> None:
        return None

    async def fake_goto(*_args, **_kwargs) -> None:
        return None

    async def fake_open_sources_tab(*_args, **_kwargs) -> None:
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return []

    async def fake_add_file_source(*_args, **_kwargs) -> None:
        calls["added"] = True

    async def fake_wait_for_source_presence(*_args, **_kwargs):
        return {"identity": "new-source.txt Document", "title": "new-source.txt Document", "text": "new-source.txt Document"}

    async def fake_wait_for_post_save_settle(*_args, **_kwargs):
        return None

    async def fake_wait_for_quiet(*_args, **_kwargs):
        return None

    async def fake_verify_persistence(*_args, **_kwargs):
        raise ResponseTimeoutError("commit was observed but refreshed card was not found")

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_open_sources_tab  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._add_project_file_source = fake_add_file_source  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fake_wait_for_source_presence  # type: ignore[method-assign]
    browser_client._wait_for_project_source_post_save_settle = fake_wait_for_post_save_settle  # type: ignore[method-assign]
    browser_client._wait_for_project_source_save_request_quiet = fake_wait_for_quiet  # type: ignore[method-assign]
    browser_client._verify_project_source_persistence = fake_verify_persistence  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._install_project_source_save_request_watch = lambda *_args, **_kwargs: {"installed": True, "finished": 1, "failed": 0, "saw_commit": True, "inflight": set()}  # type: ignore[method-assign]
    browser_client._dispose_project_source_save_request_watch = lambda *_args, **_kwargs: None  # type: ignore[method-assign]

    file_path = tmp_path / "new-source.txt"
    file_path.write_bytes(b"payload")
    result = asyncio.run(
        browser_client._add_project_source_operation(
            context=None,
            page=page,
            source_kind="file",
            value=None,
            file_path=str(file_path),
            display_name=str(file_path),
            keep_open=False,
        )
    )

    assert calls["added"] is True
    assert result["ok"] is False
    assert result["status"] == "persistence_not_verified"
    assert result["removed_existing"] is False
    assert result["persistence_false_negative_possible"] is True
    assert result["save_request_summary"]["saw_commit"] is True
    assert result["operator_review_required"] is True
    assert "verification false negative" in result["recovery_guidance"][1]


def test_add_project_source_operation_overwrites_duplicate_file_by_default(browser_client: ChatGPTBrowserClient, tmp_path: Path) -> None:
    page = object()
    snapshots = [
        [{"identity": "release.zip", "title": "release.zip", "text": "release.zip File contents may not be accessible"}],
        [],
    ]
    calls: dict[str, object] = {"removed": False, "added": False}

    async def fake_ensure_logged_in(*_args, **_kwargs) -> None:
        return None

    async def fake_goto(*_args, **_kwargs) -> None:
        return None

    async def fake_open_sources_tab(*_args, **_kwargs) -> None:
        return None

    async def fake_snapshot(*_args, **_kwargs):
        if snapshots:
            return snapshots.pop(0)
        return [{"identity": "release.zip", "title": "release.zip", "text": "release.zip"}]

    preflight_results = [
        {
            "ok": True,
            "authoritative": True,
            "reason": "stable_non_empty",
            "sources": [{"identity": "release.zip", "title": "release.zip", "text": "release.zip File contents may not be accessible"}],
            "source_count": 1,
            "empty_state_visible": False,
        },
        {
            "ok": True,
            "authoritative": True,
            "reason": "explicit_empty_state",
            "sources": [],
            "source_count": 0,
            "empty_state_visible": True,
        },
    ]

    async def fake_authoritative_preflight(*_args, **_kwargs):
        return preflight_results.pop(0)

    async def fake_remove(*_args, **kwargs):
        calls["removed"] = True
        assert kwargs["source_name"] == "release.zip"
        assert kwargs["exact"] is True
        return {"ok": True, "removed_via_ui": True, "source_match": "release.zip"}

    async def fake_add_file_source(*_args, **_kwargs) -> None:
        calls["added"] = True

    async def fake_wait_for_source_presence(*_args, **_kwargs):
        return {"identity": "release.zip", "title": "release.zip", "text": "release.zip"}

    async def fake_wait_for_post_save_settle(*_args, **_kwargs):
        return None

    async def fake_wait_for_quiet(*_args, **_kwargs):
        return None

    async def fake_verify_persistence(*_args, **_kwargs):
        return {"identity": "release.zip", "title": "release.zip", "text": "release.zip"}

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_open_sources_tab  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._wait_for_authoritative_project_sources_surface = fake_authoritative_preflight  # type: ignore[method-assign]
    browser_client._remove_project_source_operation = fake_remove  # type: ignore[method-assign]
    browser_client._add_project_file_source = fake_add_file_source  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fake_wait_for_source_presence  # type: ignore[method-assign]
    browser_client._wait_for_project_source_post_save_settle = fake_wait_for_post_save_settle  # type: ignore[method-assign]
    browser_client._wait_for_project_source_save_request_quiet = fake_wait_for_quiet  # type: ignore[method-assign]
    browser_client._verify_project_source_persistence = fake_verify_persistence  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._install_project_source_save_request_watch = lambda *_args, **_kwargs: {"installed": False}  # type: ignore[method-assign]
    browser_client._dispose_project_source_save_request_watch = lambda *_args, **_kwargs: None  # type: ignore[method-assign]

    file_path = tmp_path / "release.zip"
    file_path.write_bytes(b"zip")
    result = asyncio.run(
        browser_client._add_project_source_operation(
            context=None,
            page=page,
            source_kind="file",
            value=None,
            file_path=str(file_path),
            display_name=str(file_path),
            keep_open=False,
        )
    )

    assert calls["removed"] is True
    assert calls["added"] is True
    assert result["ok"] is True
    assert result["already_exists"] is True
    assert result["added"] is True
    assert result["overwritten"] is True
    assert result["removed_existing"] is True

def test_add_project_source_operation_returns_idempotent_success_for_duplicate_file(browser_client: ChatGPTBrowserClient, tmp_path: Path) -> None:
    page = object()

    async def fake_ensure_logged_in(*_args, **_kwargs) -> None:
        return None

    async def fake_goto(*_args, **_kwargs) -> None:
        return None

    async def fake_open_sources_tab(*_args, **_kwargs) -> None:
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return [{"identity": "candlecast-src-0.19.5.82.2.zip"}]

    async def fake_add_file_source(*_args, **_kwargs) -> None:
        return None

    async def fake_wait_for_source_presence(*_args, **kwargs):
        assert kwargs["source_match_candidates"] == ["candlecast-src-0.19.5.82.2.zip", "candlecast-src-0.19.5.82.2.zip Document"]
        return {
            "identity": "candlecast-src-0.19.5.82.2.zip",
            "title": "candlecast-src-0.19.5.82.2.zip",
            "text": "candlecast-src-0.19.5.82.2.zip",
        }

    async def fake_wait_for_post_save_settle(*_args, **_kwargs):
        raise ResponseTimeoutError("Timed out waiting for project source post-save UI to settle")

    async def fake_find_duplicate_notice(*_args, **_kwargs):
        return "candlecast-src-0.19.5.82.2.zip already exists"

    async def fake_verify_persistence(*_args, **kwargs):
        assert kwargs["source_match_candidates"] == ["candlecast-src-0.19.5.82.2.zip", "candlecast-src-0.19.5.82.2.zip Document"]
        return {
            "identity": "candlecast-src-0.19.5.82.2.zip",
            "title": "candlecast-src-0.19.5.82.2.zip",
            "text": "candlecast-src-0.19.5.82.2.zip",
        }

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_open_sources_tab  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._add_project_file_source = fake_add_file_source  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fake_wait_for_source_presence  # type: ignore[method-assign]
    browser_client._wait_for_project_source_post_save_settle = fake_wait_for_post_save_settle  # type: ignore[method-assign]
    browser_client._find_project_source_duplicate_notice = fake_find_duplicate_notice  # type: ignore[method-assign]
    browser_client._verify_project_source_persistence = fake_verify_persistence  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._install_project_source_save_request_watch = lambda *_args, **_kwargs: {"installed": False}  # type: ignore[method-assign]
    browser_client._dispose_project_source_save_request_watch = lambda *_args, **_kwargs: None  # type: ignore[method-assign]

    file_path = str(tmp_path / "candlecast-src-0.19.5.82.2.zip")
    Path(file_path).write_bytes(b"zip")
    result = asyncio.run(
        browser_client._add_project_source_operation(
            context=None,
            page=page,
            source_kind="file",
            value=None,
            file_path=file_path,
            display_name=file_path,
            keep_open=False,
            overwrite_existing=False,
        )
    )

    assert result["ok"] is True
    assert result["already_exists"] is True
    assert result["added"] is False
    assert result["source_match_requested"] == "candlecast-src-0.19.5.82.2.zip"
    assert "already exists" in result["duplicate_notice"]


class _FakeGoogleDevicePromptPage:
    url = "https://accounts.google.com/v3/signin/challenge/dp?client_id=abc"

    async def title(self):
        return "Sign in - Google Accounts"

    async def evaluate(self, _script):
        return "Check your phone Open the Google app and choose 37 to continue"


def test_google_device_prompt_url_detection(browser_client: ChatGPTBrowserClient) -> None:
    assert browser_client._is_google_device_prompt_url(
        "https://accounts.google.com/v3/signin/challenge/dp?client_id=abc"
    )
    assert not browser_client._is_google_device_prompt_url(
        "https://accounts.google.com/v3/signin/challenge/pwd?client_id=abc"
    )


def test_google_device_prompt_text_and_number_extraction(browser_client: ChatGPTBrowserClient) -> None:
    text = "Check your phone. Open the Google app and choose 37 to continue."

    assert browser_client._looks_like_google_device_prompt_text(text)
    assert browser_client._extract_google_device_prompt_numbers(text) == ["37"]


def test_google_device_prompt_snapshot_extracts_operator_number(browser_client: ChatGPTBrowserClient) -> None:
    snapshot = asyncio.run(browser_client._google_device_prompt_snapshot(_FakeGoogleDevicePromptPage()))

    assert snapshot["is_device_prompt_url"] is True
    assert snapshot["is_device_prompt_text"] is True
    assert snapshot["challenge_numbers"] == ["37"]
    assert "choose 37" in snapshot["text_preview"].lower()


def test_detect_and_log_google_device_prompt_logs_operator_instruction(browser_client: ChatGPTBrowserClient) -> None:
    events: list[tuple[str, str, dict[str, object]]] = []

    def capture_log(stage: str, message: str, **fields: object) -> None:
        events.append((stage, message, fields))

    browser_client._log = capture_log  # type: ignore[method-assign]

    detected = asyncio.run(
        browser_client._detect_and_log_google_device_prompt(
            _FakeGoogleDevicePromptPage(),
            stage="manual-login",
            iteration=1,
        )
    )

    assert detected is True
    assert any(
        stage == "google"
        and message == "operator action required"
        and fields.get("instruction") == "Choose number 37 on your phone."
        for stage, message, fields in events
    )


def test_select_project_source_capacity_prune_candidate_chooses_lowest_same_family_release(
    browser_client: ChatGPTBrowserClient,
) -> None:
    sources = [
        {
            "title": "chatgpt_claudecode_workflow_v0.0.276.18.zip",
            "identity": "chatgpt_claudecode_workflow_v0.0.276.18.zip Document",
            "text": "chatgpt_claudecode_workflow_v0.0.276.18.zip\nDocument",
            "subtitle": "Document",
        },
        {
            "title": "chatgpt_claudecode_workflow_v0.0.275.zip",
            "identity": "chatgpt_claudecode_workflow_v0.0.275.zip Document",
            "text": "chatgpt_claudecode_workflow_v0.0.275.zip\nDocument",
            "subtitle": "Document",
        },
        {
            "title": "ib_forex_trading.0.235.1.zip",
            "identity": "ib_forex_trading.0.235.1.zip Document",
            "text": "ib_forex_trading.0.235.1.zip\nDocument",
            "subtitle": "Document",
        },
    ]
    while len(sources) < 25:
        index = len(sources)
        sources.append(
            {
                "title": f"unrelated-{index}.txt",
                "identity": f"unrelated-{index}.txt Document",
                "text": f"unrelated-{index}.txt\nDocument",
                "subtitle": "Document",
            }
        )

    candidate = browser_client._select_project_source_capacity_prune_candidate(
        requested_filename="chatgpt_claudecode_workflow_v0.0.277.zip",
        source_cards=sources,
        protected_release_version="v0.0.276.18",
        protected_release_filename="chatgpt_claudecode_workflow_v0.0.276.18.zip",
    )

    assert candidate is not None
    assert candidate["filename"] == "chatgpt_claudecode_workflow_v0.0.275.zip"
    assert candidate["normalized_version"] == "v0.0.275"
    assert candidate["source_name"] == "chatgpt_claudecode_workflow_v0.0.275.zip"


def test_select_project_source_capacity_prune_candidate_requires_source_limit(
    browser_client: ChatGPTBrowserClient,
) -> None:
    sources = [
        {
            "title": "chatgpt_claudecode_workflow_v0.0.275.zip",
            "identity": "chatgpt_claudecode_workflow_v0.0.275.zip Document",
            "text": "chatgpt_claudecode_workflow_v0.0.275.zip\nDocument",
            "subtitle": "Document",
        }
    ]

    assert (
        browser_client._select_project_source_capacity_prune_candidate(
            requested_filename="chatgpt_claudecode_workflow_v0.0.277.zip",
            source_cards=sources,
        )
        is None
    )


def test_select_project_source_capacity_prune_candidates_do_not_apply_retention_below_capacity(
    browser_client: ChatGPTBrowserClient,
) -> None:
    sources = [
        {
            "title": f"chatgpt_claudecode_workflow-2_v0.1.{version}.zip",
            "identity": f"chatgpt_claudecode_workflow-2_v0.1.{version}.zip Document",
            "text": f"chatgpt_claudecode_workflow-2_v0.1.{version}.zip\nDocument",
            "subtitle": "Document",
        }
        for version in range(88, 95)
    ]

    candidates = browser_client._select_project_source_capacity_prune_candidates(
        requested_filename="chatgpt_claudecode_workflow-2_v0.1.95.zip",
        source_cards=sources,
        source_limit=25,
        retention_limit=5,
    )

    assert candidates == []


def test_select_project_source_capacity_prune_candidates_select_exactly_one_at_capacity(
    browser_client: ChatGPTBrowserClient,
) -> None:
    sources = [
        {
            "title": f"chatgpt_claudecode_workflow-2_v0.1.{version}.zip",
            "identity": f"chatgpt_claudecode_workflow-2_v0.1.{version}.zip Document",
            "text": f"chatgpt_claudecode_workflow-2_v0.1.{version}.zip\nDocument",
            "subtitle": "Document",
        }
        for version in range(88, 95)
    ]
    while len(sources) < 25:
        index = len(sources)
        sources.append({
            "title": f"docs-{index}.md",
            "identity": f"docs-{index}.md Document",
            "text": f"docs-{index}.md\nDocument",
            "subtitle": "Document",
        })

    candidates = browser_client._select_project_source_capacity_prune_candidates(
        requested_filename="chatgpt_claudecode_workflow-2_v0.1.95.zip",
        source_cards=sources,
        source_limit=25,
        retention_limit=5,
        protected_release_version="v0.1.94",
        protected_release_filename="chatgpt_claudecode_workflow-2_v0.1.94.zip",
    )

    assert [item["filename"] for item in candidates] == [
        "chatgpt_claudecode_workflow-2_v0.1.88.zip"
    ]
    assert candidates[0]["reason"] == "project_source_total_limit"
    assert candidates[0]["capacity_before"] == 25


def test_capacity_prune_requires_accepted_current_identity(
    browser_client: ChatGPTBrowserClient,
) -> None:
    sources = [
        {
            "title": f"chatgpt_claudecode_workflow-2_v0.1.103.10.{version}.zip",
            "identity": f"chatgpt_claudecode_workflow-2_v0.1.103.10.{version}.zip Zip Archive",
            "text": f"chatgpt_claudecode_workflow-2_v0.1.103.10.{version}.zip\nZip Archive",
            "subtitle": "Zip Archive",
        }
        for version in range(55, 80)
    ]

    candidate = browser_client._select_project_source_capacity_prune_candidate(
        requested_filename="chatgpt_claudecode_workflow-2_v0.1.103.10.109.zip",
        source_cards=sources,
        source_limit=25,
    )

    assert candidate is None


def test_capacity_prune_recognizes_indexed_long_versions_and_protects_current(
    browser_client: ChatGPTBrowserClient,
) -> None:
    sources = [
        {
            "title": "chatgpt_claudecode_workflow-2_v0.1.103.10.55.zip",
            "identity": "chatgpt_claudecode_workflow-2_v0.1.103.10.55.zip Zip Archive",
            "text": "chatgpt_claudecode_workflow-2_v0.1.103.10.55.zip\nZip Archive",
            "subtitle": "Zip Archive",
        },
        {
            "title": "chatgpt_claudecode_workflow-2_v0.1.103.10.68.zip",
            "identity": "chatgpt_claudecode_workflow-2_v0.1.103.10.68.zip Zip Archive",
            "text": "chatgpt_claudecode_workflow-2_v0.1.103.10.68.zip\nZip Archive",
            "subtitle": "Zip Archive",
        },
        {
            "title": "chatgpt_claudecode_workflow-2_v0.1.103.10.106(1).zip",
            "identity": "chatgpt_claudecode_workflow-2_v0.1.103.10.106(1).zip Zip Archive",
            "text": "chatgpt_claudecode_workflow-2_v0.1.103.10.106(1).zip\nZip Archive",
            "subtitle": "Zip Archive",
        },
    ]
    while len(sources) < 25:
        index = len(sources)
        sources.append({
            "title": f"docs-{index}.md",
            "identity": f"docs-{index}.md Document",
            "text": f"docs-{index}.md\nDocument",
            "subtitle": "Document",
        })

    candidate = browser_client._select_project_source_capacity_prune_candidate(
        requested_filename="chatgpt_claudecode_workflow-2_v0.1.103.10.109.zip",
        source_cards=sources,
        source_limit=25,
        protected_release_version="v0.1.103.10.68",
        protected_release_filename="chatgpt_claudecode_workflow-2_v0.1.103.10.68.zip",
    )

    assert candidate is not None
    assert candidate["filename"] == "chatgpt_claudecode_workflow-2_v0.1.103.10.55.zip"
    assert candidate["normalized_version"] == "v0.1.103.10.55"


def test_add_project_source_operation_prunes_lowest_same_family_release_at_source_limit(
    browser_client: ChatGPTBrowserClient,
    tmp_path: Path,
) -> None:
    page = object()
    release_zip = tmp_path / "chatgpt_claudecode_workflow_v0.0.277.zip"
    release_zip.write_text("fake zip fixture", encoding="utf-8")
    old_source = {
        "title": "chatgpt_claudecode_workflow_v0.0.275.zip",
        "identity": "chatgpt_claudecode_workflow_v0.0.275.zip Document",
        "text": "chatgpt_claudecode_workflow_v0.0.275.zip\nDocument",
        "subtitle": "Document",
    }
    before_sources = [
        old_source,
        {
            "title": "chatgpt_claudecode_workflow_v0.0.276.18.zip",
            "identity": "chatgpt_claudecode_workflow_v0.0.276.18.zip Document",
            "text": "chatgpt_claudecode_workflow_v0.0.276.18.zip\nDocument",
            "subtitle": "Document",
        },
    ]
    while len(before_sources) < 25:
        index = len(before_sources)
        before_sources.append(
            {
                "title": f"other-source-{index}.txt",
                "identity": f"other-source-{index}.txt Document",
                "text": f"other-source-{index}.txt\nDocument",
                "subtitle": "Document",
            }
        )
    after_prune_sources = [source for source in before_sources if source is not old_source]
    snapshot_calls = {"count": 0}
    call_order: list[str] = []

    async def fake_ensure_logged_in(*_args, **_kwargs) -> None:
        return None

    async def fake_goto(*_args, **_kwargs) -> None:
        return None

    async def fake_open_sources_tab(*_args, **_kwargs) -> None:
        return None

    async def fake_snapshot(*_args, **_kwargs):
        snapshot_calls["count"] += 1
        if snapshot_calls["count"] <= 2:
            return list(before_sources)
        return list(after_prune_sources)

    async def fake_find_existing(*_args, **_kwargs):
        return None

    async def fake_remove(*_args, **kwargs):
        call_order.append(f"remove:{kwargs['source_name']}")
        assert kwargs["source_name"] == "chatgpt_claudecode_workflow_v0.0.275.zip"
        assert kwargs["exact"] is True
        return {"ok": True, "removed_via_ui": True, "source_name": kwargs["source_name"]}

    async def fake_add_file(*_args, **_kwargs) -> None:
        call_order.append("add_file")
        after_prune_sources.append({
            "title": release_zip.name,
            "identity": f"{release_zip.name} Document",
            "text": f"{release_zip.name}\nDocument",
            "subtitle": "Document",
        })

    async def fake_wait_for_source_presence(*_args, **_kwargs):
        call_order.append("presence")
        return {
            "title": release_zip.name,
            "identity": f"{release_zip.name} Document",
            "text": f"{release_zip.name}\nDocument",
            "subtitle": "Document",
        }

    async def fake_wait_for_post_save_settle(*_args, **_kwargs):
        call_order.append("settle")
        return {"dialog_visible": False, "add_button_visible": True}

    async def fake_wait_for_save_quiet(*_args, **_kwargs):
        call_order.append("save_quiet")
        return {"quiet_now": True}

    async def fake_verify_persistence(*_args, **_kwargs):
        call_order.append("verify")
        return {
            "title": release_zip.name,
            "identity": f"{release_zip.name} Document",
            "text": f"{release_zip.name}\nDocument",
            "subtitle": "Document",
        }

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_open_sources_tab  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._find_existing_file_source_for_overwrite = fake_find_existing  # type: ignore[method-assign]
    browser_client._remove_project_source_operation = fake_remove  # type: ignore[method-assign]
    browser_client._add_project_file_source = fake_add_file  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fake_wait_for_source_presence  # type: ignore[method-assign]
    browser_client._wait_for_project_source_post_save_settle = fake_wait_for_post_save_settle  # type: ignore[method-assign]
    browser_client._wait_for_project_source_save_request_quiet = fake_wait_for_save_quiet  # type: ignore[method-assign]
    browser_client._verify_project_source_persistence = fake_verify_persistence  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._install_project_source_save_request_watch = lambda *_args, **_kwargs: {"installed": True, "started": 1, "finished": 1, "saw_relevant": True, "saw_commit": True, "inflight": set()}  # type: ignore[method-assign]
    browser_client._dispose_project_source_save_request_watch = lambda *_args, **_kwargs: None  # type: ignore[method-assign]

    result = asyncio.run(
        browser_client._add_project_source_operation(
            context=None,
            page=page,
            source_kind="file",
            value=None,
            file_path=str(release_zip),
            display_name=None,
            keep_open=False,
            protected_release_version="v0.0.276.18",
            protected_release_filename="chatgpt_claudecode_workflow_v0.0.276.18.zip",
        )
    )

    assert call_order == [
        "remove:chatgpt_claudecode_workflow_v0.0.275.zip",
        "add_file",
        "settle",
        "save_quiet",
        "verify",
    ]
    assert result["ok"] is True
    assert result["capacity_pruned"] is True
    assert result["removed_existing"] is True
    assert result["capacity_prune_result"]["source_name"] == "chatgpt_claudecode_workflow_v0.0.275.zip"
    assert result["capacity_limit"] == 25
    assert result["capacity_before"] == 25
    assert result["capacity_after_prune"] == 24
    assert result["capacity_after_upload"] == 25
    assert result["upload_started"] is True


def test_add_project_source_operation_does_not_prune_release_zips_below_capacity(
    browser_client: ChatGPTBrowserClient,
    tmp_path: Path,
) -> None:
    page = object()
    release_zip = tmp_path / "chatgpt_claudecode_workflow-2_v0.1.95.zip"
    release_zip.write_text("fake zip fixture", encoding="utf-8")
    current_sources = [
        {
            "title": f"chatgpt_claudecode_workflow-2_v0.1.{version}.zip",
            "identity": f"chatgpt_claudecode_workflow-2_v0.1.{version}.zip Document",
            "text": f"chatgpt_claudecode_workflow-2_v0.1.{version}.zip\nDocument",
            "subtitle": "Document",
        }
        for version in range(88, 95)
    ]
    current_sources.extend(
        [
            {
                "title": "docs-project-mvp.md",
                "identity": "docs-project-mvp.md Document",
                "text": "docs-project-mvp.md\nDocument",
                "subtitle": "Document",
            },
            {
                "title": "ib_forex_trading.0.248.21.zip",
                "identity": "ib_forex_trading.0.248.21.zip Document",
                "text": "ib_forex_trading.0.248.21.zip\nDocument",
                "subtitle": "Document",
            },
        ]
    )
    call_order: list[str] = []

    async def fake_ensure_logged_in(*_args, **_kwargs) -> None:
        return None

    async def fake_goto(*_args, **_kwargs) -> None:
        return None

    async def fake_open_sources_tab(*_args, **_kwargs) -> None:
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return list(current_sources)

    async def fake_find_existing(*_args, **_kwargs):
        return None

    async def fake_remove(*_args, **kwargs):
        source_name = kwargs["source_name"]
        call_order.append(f"remove:{source_name}")
        assert kwargs["exact"] is True
        current_sources[:] = [source for source in current_sources if source.get("title") != source_name]
        return {"ok": True, "removed_via_ui": True, "source_name": source_name}

    async def fake_add_file(*_args, **_kwargs) -> None:
        call_order.append("add_file")

    async def fake_wait_for_source_presence(*_args, **_kwargs):
        call_order.append("presence")
        return {
            "title": release_zip.name,
            "identity": f"{release_zip.name} Document",
            "text": f"{release_zip.name}\nDocument",
            "subtitle": "Document",
        }

    async def fake_wait_for_post_save_settle(*_args, **_kwargs):
        call_order.append("settle")
        return {"dialog_visible": False, "add_button_visible": True}

    async def fake_wait_for_save_quiet(*_args, **_kwargs):
        call_order.append("save_quiet")
        return {"quiet_now": True}

    async def fake_verify_persistence(*_args, **_kwargs):
        call_order.append("verify")
        return {
            "title": release_zip.name,
            "identity": f"{release_zip.name} Document",
            "text": f"{release_zip.name}\nDocument",
            "subtitle": "Document",
        }

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_open_sources_tab  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._find_existing_file_source_for_overwrite = fake_find_existing  # type: ignore[method-assign]
    browser_client._remove_project_source_operation = fake_remove  # type: ignore[method-assign]
    browser_client._add_project_file_source = fake_add_file  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fake_wait_for_source_presence  # type: ignore[method-assign]
    browser_client._wait_for_project_source_post_save_settle = fake_wait_for_post_save_settle  # type: ignore[method-assign]
    browser_client._wait_for_project_source_save_request_quiet = fake_wait_for_save_quiet  # type: ignore[method-assign]
    browser_client._verify_project_source_persistence = fake_verify_persistence  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._install_project_source_save_request_watch = lambda *_args, **_kwargs: {"installed": True}  # type: ignore[method-assign]
    browser_client._dispose_project_source_save_request_watch = lambda *_args, **_kwargs: None  # type: ignore[method-assign]

    result = asyncio.run(
        browser_client._add_project_source_operation(
            context=None,
            page=page,
            source_kind="file",
            value=None,
            file_path=str(release_zip),
            display_name=None,
            keep_open=False,
        )
    )

    assert call_order == ["add_file", "settle", "save_quiet", "verify"]
    assert "docs-project-mvp.md" in {source["title"] for source in current_sources}
    assert "ib_forex_trading.0.248.21.zip" in {source["title"] for source in current_sources}
    assert result["ok"] is True
    assert result["capacity_pruned"] is False
    assert result["capacity_before"] == len(current_sources)


def test_add_project_source_operation_returns_source_capacity_reached_without_upload_when_no_safe_candidate(
    browser_client: ChatGPTBrowserClient,
    tmp_path: Path,
) -> None:
    page = object()
    release_zip = tmp_path / "chatgpt_claudecode_workflow-2_v0.1.103.10.109.zip"
    release_zip.write_text("fake zip fixture", encoding="utf-8")
    sources = [
        {
            "title": f"unrelated-{index}.md",
            "identity": f"unrelated-{index}.md Document",
            "text": f"unrelated-{index}.md\nDocument",
            "subtitle": "Document",
        }
        for index in range(25)
    ]
    upload_calls: list[str] = []

    async def fake_ensure_logged_in(*_args, **_kwargs) -> None:
        return None

    async def fake_goto(*_args, **_kwargs) -> None:
        return None

    async def fake_open_sources_tab(*_args, **_kwargs) -> None:
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return list(sources)

    async def fake_add_file(*_args, **_kwargs) -> None:
        upload_calls.append("upload")

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_open_sources_tab  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._add_project_file_source = fake_add_file  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]

    result = asyncio.run(
        browser_client._add_project_source_operation(
            context=None,
            page=page,
            source_kind="file",
            value=None,
            file_path=str(release_zip),
            display_name=None,
            keep_open=False,
        )
    )

    assert result["ok"] is False
    assert result["status"] == "source_capacity_reached"
    assert result["capacity_limit"] == 25
    assert result["capacity_before"] == 25
    assert result["capacity_pruned"] is False
    assert result["upload_started"] is False
    assert upload_calls == []


def test_file_source_commit_stale_inflight_extends_persistence_readback(browser_client: ChatGPTBrowserClient) -> None:
    watch = {
        "installed": True,
        "source_kind": "file",
        "started": 2,
        "finished": 1,
        "failed": 0,
        "saw_relevant": True,
        "saw_commit": True,
        "inflight": {object()},
    }

    policy = browser_client._project_source_persistence_wait_policy(
        save_watch=watch,
        timeout_ms=15_000,
        max_refresh_attempts=3,
        retry_backoff_ms=(2_000, 4_000),
        pre_refresh_timeout_ms=10_000,
    )

    assert policy["reason"] == "file_commit_seen_stale_inflight_extended_readback"
    assert policy["timeout_ms"] >= 25_000
    assert policy["max_refresh_attempts"] >= 6
    assert policy["retry_backoff_ms"][-1] >= 16_000


def test_project_source_mutation_transaction_classifies_commit_not_visible(browser_client: ChatGPTBrowserClient) -> None:
    transaction = browser_client._project_source_mutation_transaction_status(
        save_summary={
            "source_kind": "file",
            "started": 2,
            "finished": 1,
            "failed": 0,
            "saw_relevant": True,
            "saw_commit": True,
            "inflight": 1,
        },
        persistence_verified=False,
    )

    assert transaction["transaction_status"] == "commit_seen_with_stale_inflight_not_verified_present"
    assert transaction["ambiguous"] is True
    assert transaction["release_blocking"] is True
    assert transaction["save_saw_commit"] is True
    assert transaction["save_inflight"] == 1


def test_text_source_add_uses_watch_gated_save_fallback() -> None:
    source = Path("promptbranch_browser_auth/client.py").read_text()

    assert "save_request_watch: Optional[dict[str, Any]] = None" in source
    assert "_wait_for_project_source_save_trigger_observed" in source
    assert "_trigger_project_source_text_save_fallback" in source
    assert "Control+Enter" in source
    assert "text source primary save click produced no observed save request" in source
    assert "save_request_watch=save_request_watch" in source


def test_project_source_snapshot_is_scoped_to_sources_surface(browser_client: ChatGPTBrowserClient) -> None:
    source = Path(__file__).resolve().parents[1] / "promptbranch_browser_auth" / "client.py"
    text = source.read_text()
    start = text.index("    async def _snapshot_project_source_cards")
    end = text.index("    def _source_card_identity_candidates", start)
    body = text[start:end]

    assert "looksLikeSourcesSurface" in body
    assert "if (!roots.length) return []" in body
    assert "Array.from(document.querySelectorAll('main, [role=\"main\"], body'))" not in body


def test_project_source_remove_lookup_is_scoped_to_sources_surface(browser_client: ChatGPTBrowserClient) -> None:
    source = Path(__file__).resolve().parents[1] / "promptbranch_browser_auth" / "client.py"
    text = source.read_text()
    container_start = text.index("    async def _find_project_source_container")
    container_end = text.index("    async def _find_project_source_action_button", container_start)
    container_body = text[container_start:container_end]
    action_start = text.index("    async def _find_project_source_action_button", container_end)
    action_end = text.index("    async def _find_source_options_button", action_start)
    action_body = text[action_start:action_end]

    assert "looksLikeSourcesSurface" in container_body
    assert "const roots = rootCandidates.filter(looksLikeSourcesSurface);" in container_body
    assert "if (!roots.length) return null;" in container_body
    assert "document.querySelectorAll('main *, [role=\"main\"] *, body *')" not in container_body
    assert "looksLikeSourcesSurface" in action_body
    assert "if (!roots.length) return null;" in action_body
    assert "Array.from(document.querySelectorAll('main, [role=\"main\"], body'))" not in action_body


def test_add_project_source_operation_recovers_stale_inflight_post_commit_verification_timeout(
    browser_client: ChatGPTBrowserClient,
    tmp_path: Path,
) -> None:
    page = object()
    calls: dict[str, object] = {"removed": False, "added": False, "recovered": False}

    async def fake_ensure_logged_in(*_args, **_kwargs) -> None:
        return None

    async def fake_goto(*_args, **_kwargs) -> None:
        return None

    async def fake_open_sources_tab(*_args, **_kwargs) -> None:
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return [{"identity": "release.zip", "title": "release.zip", "text": "release.zip"}]

    async def fake_remove(*_args, **kwargs):
        calls["removed"] = True
        assert kwargs["source_name"] == "release.zip"
        return {"ok": True, "removed_via_ui": True, "source_match": "release.zip"}

    async def fake_add_file_source(*_args, **_kwargs) -> None:
        calls["added"] = True

    async def fake_wait_for_source_presence(*_args, **_kwargs):
        return {"identity": "release.zip", "title": "release.zip", "text": "release.zip"}

    async def fake_wait_for_post_save_settle(*_args, **_kwargs):
        return None

    async def fake_wait_for_quiet(*_args, **_kwargs):
        return {
            "saw_commit": True,
            "started": 2,
            "finished": 1,
            "failed": 0,
            "inflight": 1,
            "stale_inflight_after_commit": True,
        }

    async def fake_verify_persistence(*_args, **_kwargs):
        raise ResponseTimeoutError("commit was observed but refreshed card was not found")

    async def fake_recover(*_args, **_kwargs):
        calls["recovered"] = True
        return {
            "identity": "release.zip",
            "title": "release.zip",
            "text": "release.zip",
            "_promptbranch_verification_mode": "post_commit_refresh_recovered",
            "_promptbranch_ui_card_seen_before_refresh": True,
            "_promptbranch_post_refresh_attempt": 2,
            "_promptbranch_post_commit_recovery": {
                "status": "recovered",
                "attempt": 2,
                "attempts": 3,
            },
        }

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_open_sources_tab  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._remove_project_source_operation = fake_remove  # type: ignore[method-assign]
    browser_client._add_project_file_source = fake_add_file_source  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fake_wait_for_source_presence  # type: ignore[method-assign]
    browser_client._wait_for_project_source_post_save_settle = fake_wait_for_post_save_settle  # type: ignore[method-assign]
    browser_client._wait_for_project_source_save_request_quiet = fake_wait_for_quiet  # type: ignore[method-assign]
    browser_client._verify_project_source_persistence = fake_verify_persistence  # type: ignore[method-assign]
    browser_client._recover_project_source_after_post_commit_timeout = fake_recover  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._install_project_source_save_request_watch = lambda *_args, **_kwargs: {  # type: ignore[method-assign]
        "installed": True,
        "source_kind": "file",
        "started": 2,
        "finished": 1,
        "failed": 0,
        "saw_relevant": True,
        "saw_commit": True,
        "inflight": {object()},
    }
    browser_client._dispose_project_source_save_request_watch = lambda *_args, **_kwargs: None  # type: ignore[method-assign]

    file_path = tmp_path / "release.zip"
    file_path.write_bytes(b"zip")
    result = asyncio.run(
        browser_client._add_project_source_operation(
            context=None,
            page=page,
            source_kind="file",
            value=None,
            file_path=str(file_path),
            display_name=str(file_path),
            keep_open=False,
        )
    )

    assert calls == {"removed": True, "added": True, "recovered": True}
    assert result["ok"] is True
    assert result["overwritten"] is True
    assert result["removed_existing"] is True
    assert result["persistence_verified"] is True
    assert result["verification_mode"] == "post_commit_refresh_recovered"
    assert result["persistence_recovered_after_commit"] is True
    assert result["post_commit_recovery"]["status"] == "recovered"


def test_post_commit_recovery_is_limited_to_stale_inflight_project_source_commit(
    browser_client: ChatGPTBrowserClient,
) -> None:
    assert browser_client._project_source_post_commit_recovery_allowed(
        source_kind="file",
        transaction={
            "transaction_status": "commit_seen_with_stale_inflight_not_verified_present",
            "save_failed": 0,
            "save_saw_commit": True,
            "save_finished": 1,
        },
    ) is True
    assert browser_client._project_source_post_commit_recovery_allowed(
        source_kind="text",
        transaction={
            "transaction_status": "commit_seen_with_stale_inflight_not_verified_present",
            "save_failed": 0,
            "save_saw_commit": True,
            "save_finished": 1,
        },
    ) is True
    assert browser_client._project_source_post_commit_recovery_allowed(
        source_kind="file",
        transaction={
            "transaction_status": "commit_seen_but_not_verified_present",
            "save_failed": 0,
            "save_saw_commit": True,
            "save_finished": 1,
        },
    ) is False


def test_add_text_project_source_operation_recovers_stale_inflight_post_commit_verification_timeout(
    browser_client: ChatGPTBrowserClient,
) -> None:
    page = object()
    calls: dict[str, object] = {"added": False, "recovered": False}

    async def fake_ensure_logged_in(*_args, **_kwargs) -> None:
        return None

    async def fake_goto(*_args, **_kwargs) -> None:
        return None

    async def fake_open_sources_tab(*_args, **_kwargs) -> None:
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return []

    async def fake_add_text_source(*_args, **_kwargs) -> None:
        calls["added"] = True

    async def fake_wait_for_source_presence(*_args, **_kwargs):
        return {"identity": "pasted.txt Document", "title": "pasted.txt Document", "text": "pasted.txt Document"}

    async def fake_wait_for_post_save_settle(*_args, **_kwargs):
        return None

    async def fake_wait_for_quiet(*_args, **_kwargs):
        return {
            "saw_commit": True,
            "started": 2,
            "finished": 1,
            "failed": 0,
            "inflight": 1,
            "stale_inflight_after_commit": True,
        }

    async def fake_verify_persistence(*_args, **_kwargs):
        raise ResponseTimeoutError("commit was observed but refreshed text card was not found")

    async def fake_recover(*_args, **_kwargs):
        calls["recovered"] = True
        return {
            "identity": "pasted.txt Document",
            "title": "pasted.txt Document",
            "text": "pasted.txt Document",
            "_promptbranch_verification_mode": "post_commit_refresh_recovered",
            "_promptbranch_ui_card_seen_before_refresh": True,
            "_promptbranch_post_refresh_attempt": 2,
            "_promptbranch_post_commit_recovery": {
                "status": "recovered",
                "attempt": 2,
                "attempts": 3,
            },
        }

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_open_sources_tab  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._add_project_textual_source = fake_add_text_source  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fake_wait_for_source_presence  # type: ignore[method-assign]
    browser_client._wait_for_project_source_post_save_settle = fake_wait_for_post_save_settle  # type: ignore[method-assign]
    browser_client._wait_for_project_source_save_request_quiet = fake_wait_for_quiet  # type: ignore[method-assign]
    browser_client._verify_project_source_persistence = fake_verify_persistence  # type: ignore[method-assign]
    browser_client._recover_project_source_after_post_commit_timeout = fake_recover  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._install_project_source_save_request_watch = lambda *_args, **_kwargs: {  # type: ignore[method-assign]
        "installed": True,
        "source_kind": "text",
        "started": 2,
        "finished": 1,
        "failed": 0,
        "saw_relevant": True,
        "saw_commit": True,
        "inflight": {object()},
    }
    browser_client._dispose_project_source_save_request_watch = lambda *_args, **_kwargs: None  # type: ignore[method-assign]

    result = asyncio.run(
        browser_client._add_project_source_operation(
            context=None,
            page=page,
            source_kind="text",
            value="Integration note for run 20260620-192032-1098158",
            file_path=None,
            display_name="itest-text-20260620-192032-1098158",
            keep_open=False,
        )
    )

    assert calls["added"] is True
    assert calls["recovered"] is True
    assert result["ok"] is True
    assert result["source_kind"] == "text"
    assert result["persistence_recovered_after_commit"] is True
    assert result["verification_mode"] == "post_commit_refresh_recovered"
    assert result["post_commit_recovery"]["status"] == "recovered"


def test_text_commit_seen_stale_inflight_extends_persistence_readback(
    browser_client: ChatGPTBrowserClient,
) -> None:
    policy = browser_client._project_source_persistence_wait_policy(
        save_watch={
            "source_kind": "text",
            "saw_commit": True,
            "failed": 0,
            "inflight": {object()},
        },
        timeout_ms=15_000,
        max_refresh_attempts=3,
        retry_backoff_ms=(2_000, 4_000),
        pre_refresh_timeout_ms=10_000,
    )

    assert policy["reason"] == "text_commit_seen_stale_inflight_extended_readback"
    assert policy["timeout_ms"] >= 25_000
    assert policy["max_refresh_attempts"] >= 6


def test_text_post_commit_recovery_failure_reports_specific_status(
    browser_client: ChatGPTBrowserClient,
) -> None:
    page = object()

    async def fake_ensure_logged_in(*_args, **_kwargs) -> None:
        return None

    async def fake_goto(*_args, **_kwargs) -> None:
        return None

    async def fake_open_sources_tab(*_args, **_kwargs) -> None:
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return []

    async def fake_add_text_source(*_args, **_kwargs) -> None:
        return None

    async def fake_wait_for_source_presence(*_args, **_kwargs):
        raise ResponseTimeoutError("not found")

    async def fake_wait_for_post_save_settle(*_args, **_kwargs):
        return None

    async def fake_wait_for_quiet(*_args, **_kwargs):
        return {"saw_commit": True, "started": 2, "finished": 1, "failed": 0, "inflight": 1}

    async def fake_verify_persistence(*_args, **_kwargs):
        raise ResponseTimeoutError("commit was observed but refreshed text card was not found")

    async def fake_recover(*_args, **_kwargs):
        return None

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_open_sources_tab  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._add_project_textual_source = fake_add_text_source  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fake_wait_for_source_presence  # type: ignore[method-assign]
    browser_client._wait_for_project_source_post_save_settle = fake_wait_for_post_save_settle  # type: ignore[method-assign]
    browser_client._wait_for_project_source_save_request_quiet = fake_wait_for_quiet  # type: ignore[method-assign]
    browser_client._verify_project_source_persistence = fake_verify_persistence  # type: ignore[method-assign]
    browser_client._recover_project_source_after_post_commit_timeout = fake_recover  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._install_project_source_save_request_watch = lambda *_args, **_kwargs: {  # type: ignore[method-assign]
        "installed": True,
        "source_kind": "text",
        "started": 2,
        "finished": 1,
        "failed": 0,
        "saw_relevant": True,
        "saw_commit": True,
        "inflight": {object()},
    }
    browser_client._dispose_project_source_save_request_watch = lambda *_args, **_kwargs: None  # type: ignore[method-assign]

    result = asyncio.run(
        browser_client._add_project_source_operation(
            context=None,
            page=page,
            source_kind="text",
            value="Integration note for run 20260620-192032-1098158",
            file_path=None,
            display_name="itest-text-20260620-192032-1098158",
            keep_open=False,
        )
    )

    assert result["ok"] is False
    assert result["status"] == "post_commit_source_surface_not_refreshed"
    assert result["post_commit_recovery"] == {"attempted": True, "status": "not_recovered"}
    assert result["persistence_false_negative_possible"] is True
    assert result["release_blocking"] is True
    assert result["operator_review_required"] is True
    assert result["transaction_status"] == "commit_seen_with_stale_inflight_not_verified_present"
    assert result["source_mutation_transaction"]["release_blocking"] is True
    assert any("pb src list --json" in item for item in result["recovery_guidance"])


def test_add_text_project_source_operation_reconciles_committed_text_from_post_commit_source_list(
    browser_client: ChatGPTBrowserClient,
) -> None:
    page = object()
    snapshot_calls = {"count": 0}

    async def fake_ensure_logged_in(*_args, **_kwargs) -> None:
        return None

    async def fake_goto(*_args, **_kwargs) -> None:
        return None

    async def fake_open_sources_tab(*_args, **_kwargs) -> None:
        return None

    async def fake_snapshot(*_args, **_kwargs):
        snapshot_calls["count"] += 1
        if snapshot_calls["count"] >= 3:
            return [
                {
                    "identity": "itest-text-20260627T-reconcile Document",
                    "title": "itest-text-20260627T-reconcile Document",
                    "text": "itest-text-20260627T-reconcile Document",
                }
            ]
        return []

    async def fake_add_text_source(*_args, **_kwargs) -> None:
        return None

    async def fake_wait_for_source_presence(*_args, **_kwargs):
        raise ResponseTimeoutError("source surface did not refresh")

    async def fake_wait_for_post_save_settle(*_args, **_kwargs) -> None:
        return None

    async def fake_wait_for_quiet(*_args, **_kwargs):
        return {"saw_commit": True, "started": 2, "finished": 1, "failed": 0, "inflight": 1}

    async def fake_verify_persistence(*_args, **_kwargs):
        raise ResponseTimeoutError("commit was observed but refreshed text card was not found")

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_open_sources_tab  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._add_project_textual_source = fake_add_text_source  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fake_wait_for_source_presence  # type: ignore[method-assign]
    browser_client._wait_for_project_source_post_save_settle = fake_wait_for_post_save_settle  # type: ignore[method-assign]
    browser_client._wait_for_project_source_save_request_quiet = fake_wait_for_quiet  # type: ignore[method-assign]
    browser_client._verify_project_source_persistence = fake_verify_persistence  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._install_project_source_save_request_watch = lambda *_args, **_kwargs: {  # type: ignore[method-assign]
        "installed": True,
        "source_kind": "text",
        "started": 2,
        "finished": 1,
        "failed": 0,
        "saw_relevant": True,
        "saw_commit": True,
        "inflight": {object()},
    }
    browser_client._dispose_project_source_save_request_watch = lambda *_args, **_kwargs: None  # type: ignore[method-assign]

    result = asyncio.run(
        browser_client._add_project_source_operation(
            context=None,
            page=page,
            source_kind="text",
            value="Integration note for run 20260627T-reconcile\nbody",
            file_path=None,
            display_name="itest-text-20260627T-reconcile",
            keep_open=False,
        )
    )

    assert result["ok"] is True
    assert result["source_kind"] == "text"
    assert result["persistence_verified"] is True
    assert result["persistence_recovered_after_commit"] is True
    assert result["verification_mode"] == "post_commit_text_source_list_reconciled"
    assert result["post_commit_recovery"]["status"] == "recovered_by_text_source_reconciliation"
    assert result["post_commit_recovery"]["proof"]["text_source_reconciliation_verified"] is True


def test_text_source_post_commit_reconciliation_rejects_nearby_different_text_source(
    browser_client: ChatGPTBrowserClient,
) -> None:
    recovered = browser_client._find_text_source_post_commit_reconciliation_match(
        [
            {
                "identity": "itest-text-20260627T-other Document",
                "title": "itest-text-20260627T-other Document",
                "text": "itest-text-20260627T-other Document",
            }
        ],
        value="Integration note for run 20260627T-expected\nbody",
        display_name="itest-text-20260627T-expected",
        source_match_candidates=["itest-text-20260627T-expected", "Integration note for run 20260627T-expected"],
    )

    assert recovered is None


def test_text_source_post_commit_reconciliation_rejects_visible_zip_source(
    browser_client: ChatGPTBrowserClient,
) -> None:
    recovered = browser_client._find_text_source_post_commit_reconciliation_match(
        [
            {
                "identity": "chatgpt_claudecode_workflow-2_v0.1.97.zip Zip Archive",
                "title": "chatgpt_claudecode_workflow-2_v0.1.97.zip",
                "subtitle": "Zip Archive",
                "text": "chatgpt_claudecode_workflow-2_v0.1.97.zip Zip Archive",
            }
        ],
        value="Integration note for run 20260627T-expected\nbody",
        display_name="itest-text-20260627T-expected",
        source_match_candidates=["chatgpt_claudecode_workflow-2_v0.1.97.zip", "itest-text-20260627T-expected"],
    )

    assert recovered is None




def test_text_post_commit_recovery_reopens_sources_surface_before_accepting_exact_text_proof(
    browser_client: ChatGPTBrowserClient,
) -> None:
    class Page:
        async def wait_for_timeout(self, _ms):
            return None

    page = Page()
    calls = {"goto": 0, "open_tab": 0, "snapshot": 0}

    async def fake_goto(*_args, **_kwargs):
        calls["goto"] += 1
        return None

    async def fake_open_sources_tab(*_args, **_kwargs):
        calls["open_tab"] += 1
        return None

    async def fake_snapshot(*_args, **_kwargs):
        calls["snapshot"] += 1
        if calls["snapshot"] >= 2:
            return [
                {
                    "identity": "itest-text-v1001-recovery Document",
                    "title": "itest-text-v1001-recovery Document",
                    "text": "itest-text-v1001-recovery Document",
                }
            ]
        return []

    async def fake_empty_state(*_args, **_kwargs):
        return False

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    async def fake_wait_for_source_presence(*_args, **_kwargs):
        raise ResponseTimeoutError("generic presence wait should not be needed once exact text proof appears")

    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_open_sources_tab  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._project_sources_empty_state_visible = fake_empty_state  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fake_wait_for_source_presence  # type: ignore[method-assign]

    recovered = asyncio.run(
        browser_client._recover_project_source_after_post_commit_timeout(
            page,
            project_url="https://chatgpt.com/g/g-p-123/project",
            source_match_candidates=["itest-text-v1001-recovery"],
            source_kind="text",
            value="itest-text-v1001-recovery\nbody",
            display_name="itest-text-v1001-recovery",
            original_error="commit seen but source surface did not refresh",
            attempts=1,
            timeout_ms=5_000,
            backoff_ms=(),
        )
    )

    assert recovered is not None
    assert calls["open_tab"] >= 1
    assert recovered["_promptbranch_verification_mode"] == "post_commit_text_source_list_reconciled"
    assert recovered["_promptbranch_post_commit_recovery"]["surface_probe"]["sources_tab_opened"] is True
    assert recovered["_promptbranch_post_commit_recovery"]["surface_probe"]["matched"] is True


def test_text_post_commit_recovery_records_empty_surface_diagnostics_when_not_recovered(
    browser_client: ChatGPTBrowserClient,
) -> None:
    class Page:
        async def wait_for_timeout(self, _ms):
            return None

    page = Page()

    async def fake_goto(*_args, **_kwargs):
        return None

    async def fake_open_sources_tab(*_args, **_kwargs):
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return []

    async def fake_empty_state(*_args, **_kwargs):
        return False

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    async def fake_wait_for_source_presence(*_args, **_kwargs):
        raise ResponseTimeoutError("source list stayed empty")

    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_open_sources_tab  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._project_sources_empty_state_visible = fake_empty_state  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fake_wait_for_source_presence  # type: ignore[method-assign]

    recovered = asyncio.run(
        browser_client._recover_project_source_after_post_commit_timeout(
            page,
            project_url="https://chatgpt.com/g/g-p-123/project",
            source_match_candidates=["itest-text-v1001-missing"],
            source_kind="text",
            value="itest-text-v1001-missing\nbody",
            display_name="itest-text-v1001-missing",
            original_error="commit seen but source surface stayed empty",
            attempts=1,
            timeout_ms=5_000,
            backoff_ms=(),
        )
    )

    diagnostics = getattr(browser_client, "_last_project_source_post_commit_recovery_diagnostics")
    assert recovered is None
    assert diagnostics["status"] == "not_recovered"
    assert diagnostics["surface_empty_or_unreadable"] is True
    assert diagnostics["source_card_count"] == 0
    assert diagnostics["last_surface_probe"]["sources_tab_opened"] is True
    assert diagnostics["last_surface_probe"]["surface_empty_or_unreadable"] is True


def test_text_source_document_conversion_candidates_use_first_line_and_display_name(
    browser_client: ChatGPTBrowserClient,
) -> None:
    value = "\n".join([
        "Integration note for run 20260620-152824-163044",
        "Promptbranch text-source document conversion proof.",
        *(f"filler-{index:04d}" for index in range(1400)),
    ])

    assert browser_client._text_source_document_conversion_expected(value)
    candidates = browser_client._build_source_match_candidates(
        "text",
        value=value,
        display_name="itest-text-20260620-152824-163044",
        file_path=None,
    )

    assert "Integration note for run 20260620-152824-163044.txt Document" in candidates
    assert "itest-text-20260620-152824-163044.txt Document" in candidates


def test_text_source_document_conversion_content_proof_rejects_generic_old_pasted_document(
    browser_client: ChatGPTBrowserClient,
) -> None:
    proof = browser_client._text_source_card_content_proof(
        {"identity": "pasted.txt Document", "title": "pasted.txt", "text": "pasted.txt\nDocument"},
        value="Integration note for run 20260620-152824-163044\nbody",
        display_name="itest-text-20260620-152824-163044",
    )

    assert proof["content_match_verified"] is False
    assert proof["generic_document_only"] is True


def test_text_source_document_conversion_content_proof_accepts_run_id_filename(
    browser_client: ChatGPTBrowserClient,
) -> None:
    proof = browser_client._text_source_card_content_proof(
        {
            "identity": "Integration note for run 20260620-152824-163044.txt Document",
            "title": "Integration note for run 20260620-152824-163044.txt",
            "text": "Integration note for run 20260620-152824-163044.txt\nDocument",
        },
        value="Integration note for run 20260620-152824-163044\nbody",
        display_name="itest-text-20260620-152824-163044",
    )

    assert proof["content_match_verified"] is True
    assert proof["matched_anchor"] == "Integration note for run 20260620-152824-163044"


def test_select_text_test_capacity_prune_candidate_is_limited_to_safe_test_sources(
    browser_client: ChatGPTBrowserClient,
) -> None:
    sources = [
        {"identity": "customer-notes.txt Document", "title": "customer-notes.txt", "text": "customer-notes.txt Document"},
        {"identity": "itest-file-20260619-200759-3669939.txt Document", "title": "itest-file-20260619-200759-3669939.txt", "text": "itest-file-20260619-200759-3669939.txt Document"},
        {"identity": "pasted.txt Document", "title": "pasted.txt", "text": "pasted.txt Document"},
        {"identity": "other.txt Document", "title": "other.txt", "text": "other.txt Document"},
        {"identity": "more.txt Document", "title": "more.txt", "text": "more.txt Document"},
    ]

    candidate = browser_client._select_project_source_text_test_capacity_prune_candidate(
        value="Integration note for run 20260620-152824-163044",
        display_name="itest-text-20260620-152824-163044",
        source_cards=sources,
        source_limit=5,
    )

    assert candidate is not None
    assert candidate["source_name"] == "pasted.txt"
    assert candidate["reason"] == "text_test_source_capacity_prune"

    assert browser_client._select_project_source_text_test_capacity_prune_candidate(
        value="real user note",
        display_name="real-note",
        source_cards=sources,
        source_limit=5,
    ) is None


def test_text_source_document_conversion_dedicated_name_is_characterization_only(
    browser_client: ChatGPTBrowserClient,
) -> None:
    generic_proof = browser_client._text_source_card_content_proof(
        {"identity": "pasted.txt Document", "title": "pasted.txt", "text": "pasted.txt\nDocument"},
        value="Integration note for run 20260620-160620-308713\nbody",
        display_name="itest-text-20260620-160620-308713",
    )
    named_proof = browser_client._text_source_card_content_proof(
        {
            "identity": "Integration note for run 20260620-160620-308713.txt Document",
            "title": "Integration note for run 20260620-160620-308713.txt",
            "text": "Integration note for run 20260620-160620-308713.txt\nDocument",
        },
        value="Integration note for run 20260620-160620-308713\nbody",
        display_name="itest-text-20260620-160620-308713",
    )
    generated_non_generic_without_anchor = browser_client._text_source_card_content_proof(
        {
            "identity": "json-orchestration-state.txt Document",
            "title": "json-orchestration-state.txt",
            "text": "json-orchestration-state.txt\nDocument",
        },
        value="Integration note for run 20260620-160620-308713\nbody",
        display_name="itest-text-20260620-160620-308713",
    )

    assert browser_client._text_source_document_conversion_requires_dedicated_name_failure(
        generic_proof,
        conversion_expected=True,
        source_saved_as_document=True,
    ) is False
    assert browser_client._text_source_document_conversion_requires_dedicated_name_failure(
        named_proof,
        conversion_expected=True,
        source_saved_as_document=True,
    ) is False
    assert browser_client._text_source_document_conversion_requires_dedicated_name_failure(
        generic_proof,
        conversion_expected=False,
        source_saved_as_document=True,
    ) is False
    assert browser_client._text_source_document_conversion_requires_dedicated_name_failure(
        generated_non_generic_without_anchor,
        conversion_expected=True,
        source_saved_as_document=True,
    ) is False


def test_large_text_source_legacy_pasted_document_is_non_blocking_characterization(
    browser_client: ChatGPTBrowserClient,
) -> None:
    page = object()
    run_id = "20260620-160620-308713"
    value = "\n".join([
        f"Integration note for run {run_id}",
        "Promptbranch text-source document conversion proof.",
        *(f"document-conversion-filler-{run_id}-{index:04d}" for index in range(700)),
    ])

    assert browser_client._text_source_document_conversion_expected(value)

    async def fake_ensure_logged_in(*_args, **_kwargs) -> None:
        return None

    async def fake_goto(*_args, **_kwargs) -> None:
        return None

    async def fake_open_sources_tab(*_args, **_kwargs) -> None:
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return []

    async def fake_add_textual_source(*_args, **_kwargs) -> None:
        return None

    async def fake_wait_for_source_presence(*_args, **_kwargs):
        raise ResponseTimeoutError("Timed out waiting for project source to appear")

    async def fake_wait_for_post_save_settle(*_args, **_kwargs):
        return {"dialog_visible": False, "source_card_count": 1}

    async def fake_wait_for_save_quiet(*_args, **_kwargs):
        return {"saw_relevant": True, "saw_commit": True, "started": 2, "finished": 2, "failed": 0, "inflight": 0}

    async def fake_verify_persistence(*_args, **_kwargs):
        return {"identity": "pasted.txt Document", "title": "pasted.txt", "subtitle": "Document", "text": "pasted.txt\nDocument"}

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_open_sources_tab  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._add_project_textual_source = fake_add_textual_source  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fake_wait_for_source_presence  # type: ignore[method-assign]
    browser_client._wait_for_project_source_post_save_settle = fake_wait_for_post_save_settle  # type: ignore[method-assign]
    browser_client._wait_for_project_source_save_request_quiet = fake_wait_for_save_quiet  # type: ignore[method-assign]
    browser_client._verify_project_source_persistence = fake_verify_persistence  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._install_project_source_save_request_watch = lambda *_args, **_kwargs: {"installed": True}  # type: ignore[method-assign]
    browser_client._dispose_project_source_save_request_watch = lambda *_args, **_kwargs: None  # type: ignore[method-assign]

    result = asyncio.run(
        browser_client._add_project_source_operation(
            context=None,
            page=page,
            source_kind="text",
            value=value,
            file_path=None,
            display_name=f"itest-text-{run_id}",
            keep_open=False,
        )
    )

    assert result["ok"] is True
    assert result["persistence_verified"] is True
    assert result["source_saved_as_document"] is True
    assert result["source_content_match_verified"] is False
    assert result["text_source_content_proof"]["generic_document_only"] is True
    assert result["text_source_content_proof"]["legacy_pasted_document_seen"] is True
    assert result["dedicated_document_name_detected"] is False
    assert result["legacy_pasted_document_seen"] is True
    assert result["content_verification_release_blocking"] is False
    assert result["document_conversion_characterization_status"] == "generic_document_identity_seen"


def test_file_project_source_add_waits_for_normal_quiet_not_stale_soft_quiet(
    browser_client: ChatGPTBrowserClient,
    tmp_path: Path,
) -> None:
    page = object()
    captured: dict[str, object] = {}

    async def fake_ensure_logged_in(*_args, **_kwargs) -> None:
        return None

    async def fake_goto(*_args, **_kwargs) -> None:
        return None

    async def fake_open_sources_tab(*_args, **_kwargs) -> None:
        return None

    async def fake_find_existing(*_args, **_kwargs):
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return []

    async def fake_add_file_source(*_args, **_kwargs) -> None:
        return None

    async def fake_wait_for_source_presence(*_args, **_kwargs):
        return {"identity": "release.zip", "title": "release.zip", "text": "release.zip"}

    async def fake_wait_for_post_save_settle(*_args, **_kwargs):
        return {"settled": True}

    async def fake_wait_for_quiet(*_args, **kwargs):
        captured["timeout_ms"] = kwargs.get("timeout_ms")
        captured["allow_stale_inflight_after_commit"] = kwargs.get("allow_stale_inflight_after_commit")
        return {
            "saw_commit": True,
            "started": 2,
            "finished": 2,
            "failed": 0,
            "inflight": 0,
        }

    async def fake_verify_persistence(*_args, **_kwargs):
        return {
            "identity": "release.zip",
            "title": "release.zip",
            "text": "release.zip",
            "_promptbranch_verification_mode": "post_refresh",
        }

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_open_sources_tab  # type: ignore[method-assign]
    browser_client._find_existing_file_source_for_overwrite = fake_find_existing  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._add_project_file_source = fake_add_file_source  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fake_wait_for_source_presence  # type: ignore[method-assign]
    browser_client._wait_for_project_source_post_save_settle = fake_wait_for_post_save_settle  # type: ignore[method-assign]
    browser_client._wait_for_project_source_save_request_quiet = fake_wait_for_quiet  # type: ignore[method-assign]
    browser_client._verify_project_source_persistence = fake_verify_persistence  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._install_project_source_save_request_watch = lambda *_args, **_kwargs: {  # type: ignore[method-assign]
        "installed": True,
        "source_kind": "file",
        "started": 2,
        "finished": 1,
        "failed": 0,
        "saw_relevant": True,
        "saw_commit": True,
        "inflight": {object()},
    }
    browser_client._dispose_project_source_save_request_watch = lambda *_args, **_kwargs: None  # type: ignore[method-assign]

    file_path = tmp_path / "release.zip"
    file_path.write_bytes(b"zip")
    result = asyncio.run(
        browser_client._add_project_source_operation(
            context=None,
            page=page,
            source_kind="file",
            value=None,
            file_path=str(file_path),
            display_name=str(file_path),
            keep_open=False,
        )
    )

    assert result["ok"] is True
    assert captured["allow_stale_inflight_after_commit"] is False
    assert captured["timeout_ms"] == 60_000


def test_add_file_source_operation_recovers_post_commit_visible_snapshot_after_recovery_timeout(
    browser_client: ChatGPTBrowserClient,
    tmp_path: Path,
) -> None:
    page = object()
    snapshot_calls = {"count": 0}
    recovery_called = {"value": False}

    async def fake_ensure_logged_in(*_args, **_kwargs) -> None:
        return None

    async def fake_goto(*_args, **_kwargs) -> None:
        return None

    async def fake_open_sources_tab(*_args, **_kwargs) -> None:
        return None

    async def fake_find_existing(*_args, **_kwargs):
        return None

    async def fake_snapshot(*_args, **_kwargs):
        snapshot_calls["count"] += 1
        if snapshot_calls["count"] <= 1:
            return []
        return [{"identity": "release.zip", "title": "release.zip", "text": "release.zip Document"}]

    async def fake_add_file_source(*_args, **_kwargs) -> None:
        return None

    async def fake_wait_for_source_presence(*_args, **_kwargs):
        return {"identity": "release.zip", "title": "release.zip", "text": "release.zip Document"}

    async def fake_wait_for_post_save_settle(*_args, **_kwargs):
        return {"settled": True}

    async def fake_wait_for_quiet(*_args, **_kwargs):
        return {
            "saw_commit": True,
            "started": 2,
            "finished": 1,
            "failed": 0,
            "inflight": 1,
            "stale_inflight_after_commit": True,
        }

    async def fake_verify_persistence(*_args, **_kwargs):
        raise ResponseTimeoutError("post-refresh surface did not verify the committed source")

    async def fake_recover(*_args, **_kwargs):
        recovery_called["value"] = True
        return None

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    browser_client._goto = fake_goto  # type: ignore[method-assign]
    async def fake_preflight(*_args, **_kwargs):
        return {"ok": True, "status": "authoritative_empty", "sources": [], "source_card_count": 0, "source_identities": [], "empty_state_visible": True}

    browser_client._open_project_sources_tab = fake_open_sources_tab  # type: ignore[method-assign]
    browser_client._wait_for_authoritative_project_sources_surface = fake_preflight  # type: ignore[method-assign]
    browser_client._find_existing_file_source_for_overwrite = fake_find_existing  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._add_project_file_source = fake_add_file_source  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fake_wait_for_source_presence  # type: ignore[method-assign]
    browser_client._wait_for_project_source_post_save_settle = fake_wait_for_post_save_settle  # type: ignore[method-assign]
    browser_client._wait_for_project_source_save_request_quiet = fake_wait_for_quiet  # type: ignore[method-assign]
    browser_client._verify_project_source_persistence = fake_verify_persistence  # type: ignore[method-assign]
    browser_client._recover_project_source_after_post_commit_timeout = fake_recover  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._install_project_source_save_request_watch = lambda *_args, **_kwargs: {  # type: ignore[method-assign]
        "installed": True,
        "source_kind": "file",
        "started": 2,
        "finished": 1,
        "failed": 0,
        "saw_relevant": True,
        "saw_commit": True,
        "inflight": {object()},
    }
    browser_client._dispose_project_source_save_request_watch = lambda *_args, **_kwargs: None  # type: ignore[method-assign]

    file_path = tmp_path / "release.zip"
    file_path.write_bytes(b"zip")
    result = asyncio.run(
        browser_client._add_project_source_operation(
            context=None,
            page=page,
            source_kind="file",
            value=None,
            file_path=str(file_path),
            display_name=str(file_path),
            keep_open=False,
        )
    )

    assert recovery_called["value"] is True
    assert result["ok"] is True
    assert result["persistence_verified"] is True
    assert result["verification_mode"] == "post_commit_surface_snapshot_recovered"
    assert result["persistence_recovered_after_commit"] is True
    assert result["post_commit_recovery"]["status"] == "recovered_from_visible_surface_snapshot"



def test_file_source_duplicate_suffix_match_is_exact_and_suffix_bound(
    browser_client: ChatGPTBrowserClient,
) -> None:
    details = browser_client._file_source_duplicate_suffix_match_details(
        requested_candidates=["release.zip", "release.zip Document"],
        observed_identity="release(1).zip Document",
    )

    assert details == {
        "requested": "release.zip",
        "observed": "release(1).zip",
        "observed_without_duplicate_suffix": "release.zip",
        "match_kind": "file_duplicate_suffix",
    }
    assert browser_client._file_source_duplicate_suffix_match_details(
        requested_candidates=["release.zip"],
        observed_identity="other-release(1).zip Document",
    ) is None
    assert browser_client._file_source_duplicate_suffix_match_details(
        requested_candidates=["release.zip"],
        observed_identity="release-copy.zip Document",
    ) is None
    assert browser_client._file_source_exact_canonical_match_details(
        requested_candidates=["release.zip", "release.zip Document"],
        observed_identity="release.zip Document",
    ) == {
        "requested": "release.zip",
        "observed": "release.zip",
        "match_kind": "file_exact_canonical",
    }
    assert browser_client._file_source_exact_canonical_match_details(
        requested_candidates=["release.zip"],
        observed_identity="release(1).zip Document",
    ) is None


def test_same_name_file_overwrite_uses_in_place_replace_without_library_preflight(
    browser_client: ChatGPTBrowserClient,
    tmp_path: Path,
) -> None:
    context = _LibraryWatchContext()
    page = _LibraryPage()
    existing = {
        "identity": "release.zip Document",
        "title": "release.zip",
        "text": "release.zip Document",
        "file_id": "file_existing_123",
    }
    calls = {"replace": 0, "library": 0, "remove": 0, "upload": 0}

    async def fake_noop(*_args, **_kwargs) -> None:
        return None

    async def fake_authoritative(*_args, **_kwargs):
        return {
            "ok": True,
            "authoritative": True,
            "sources": [existing],
            "source_card_count": 1,
            "source_identities": ["release.zip Document"],
            "empty_state_visible": False,
        }

    async def fake_replace(*_args, **kwargs):
        calls["replace"] += 1
        assert kwargs["existing_source"] == existing
        assert kwargs["canonical_name"] == "release.zip"
        return {
            "ok": True,
            "action": "add",
            "status": "verified_present",
            "persistence_verified": True,
            "overwritten": True,
            "removed_existing": False,
            "replacement_mode": "in_place_ui",
            "backend_assigned_name": "release.zip",
            "exact_canonical_source_count": 1,
            "duplicate_suffix_source_count": 0,
        }

    async def forbidden_library(*_args, **_kwargs):
        calls["library"] += 1
        raise AssertionError("normal same-name replace must not inspect Library")

    async def forbidden_remove(*_args, **_kwargs):
        calls["remove"] += 1
        raise AssertionError("normal same-name replace must not remove the source")

    async def forbidden_upload(*_args, **_kwargs):
        calls["upload"] += 1
        raise AssertionError("normal same-name replace must not use Add source")

    browser_client.ensure_logged_in = fake_noop  # type: ignore[method-assign]
    browser_client._goto = fake_noop  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_noop  # type: ignore[method-assign]
    browser_client._wait_for_authoritative_project_sources_surface = fake_authoritative  # type: ignore[method-assign]
    browser_client._replace_project_file_source_operation = fake_replace  # type: ignore[method-assign]
    browser_client._reconcile_library_file_family = forbidden_library  # type: ignore[method-assign]
    browser_client._remove_project_source_operation = forbidden_remove  # type: ignore[method-assign]
    browser_client._add_project_file_source = forbidden_upload  # type: ignore[method-assign]

    file_path = tmp_path / "release.zip"
    file_path.write_bytes(b"zip")
    result = asyncio.run(
        browser_client._add_project_source_operation(
            context=context,
            page=page,
            source_kind="file",
            value=None,
            file_path=str(file_path),
            display_name=str(file_path),
        )
    )

    assert result["ok"] is True
    assert result["replacement_mode"] == "in_place_ui"
    assert result["removed_existing"] is False
    assert calls == {"replace": 1, "library": 0, "remove": 0, "upload": 0}


def test_existing_source_replace_capability_failure_is_non_destructive(
    browser_client: ChatGPTBrowserClient,
    tmp_path: Path,
) -> None:
    context = _LibraryWatchContext()
    page = _LibraryPage()
    existing = {
        "identity": "release.zip Document",
        "title": "release.zip",
        "text": "release.zip Document",
        "file_id": "file_existing_123",
    }
    calls = {"library": 0, "remove": 0, "upload": 0}

    async def fake_noop(*_args, **_kwargs) -> None:
        return None

    async def fake_authoritative(*_args, **_kwargs):
        return {
            "ok": True,
            "authoritative": True,
            "sources": [existing],
            "source_card_count": 1,
            "source_identities": ["release.zip Document"],
            "empty_state_visible": False,
        }

    async def fake_replace(*_args, **_kwargs):
        return {
            "ok": False,
            "action": "add",
            "status": "project_source_replace_not_supported",
            "persistence_verified": False,
            "project_source_mutated": False,
            "release_blocking": True,
            "operator_review_required": True,
            "visible_source_actions": ["Remove"],
        }

    async def forbidden_library(*_args, **_kwargs):
        calls["library"] += 1
        raise AssertionError("replace capability failure must not inspect Library")

    async def forbidden_remove(*_args, **_kwargs):
        calls["remove"] += 1
        raise AssertionError("replace capability failure must not remove source")

    async def forbidden_upload(*_args, **_kwargs):
        calls["upload"] += 1
        raise AssertionError("replace capability failure must not upload")

    browser_client.ensure_logged_in = fake_noop  # type: ignore[method-assign]
    browser_client._goto = fake_noop  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_noop  # type: ignore[method-assign]
    browser_client._wait_for_authoritative_project_sources_surface = fake_authoritative  # type: ignore[method-assign]
    browser_client._replace_project_file_source_operation = fake_replace  # type: ignore[method-assign]
    browser_client._reconcile_library_file_family = forbidden_library  # type: ignore[method-assign]
    browser_client._remove_project_source_operation = forbidden_remove  # type: ignore[method-assign]
    browser_client._add_project_file_source = forbidden_upload  # type: ignore[method-assign]

    file_path = tmp_path / "release.zip"
    file_path.write_bytes(b"zip")
    result = asyncio.run(
        browser_client._add_project_source_operation(
            context=context,
            page=page,
            source_kind="file",
            value=None,
            file_path=str(file_path),
            display_name=str(file_path),
        )
    )

    assert result["ok"] is False
    assert result["status"] == "project_source_replace_not_supported"
    assert result["project_source_mutated"] is False
    assert calls == {"library": 0, "remove": 0, "upload": 0}




def test_add_file_source_operation_increments_existing_indexed_family_once(browser_client: ChatGPTBrowserClient, tmp_path: Path) -> None:
    page = object()
    old_card = {"identity": "release(14).zip Document", "title": "release(14).zip", "text": "release(14).zip Document"}
    new_card = {"identity": "release(15).zip Document", "title": "release(15).zip", "text": "release(15).zip Document"}
    calls = {"uploads": 0, "generic_verify": 0}
    processed_file_id = "file_000000001234567890abcdef12345678"
    library_object_id = "libfile_1234567890abcdef1234567890abcdef"

    async def fake_noop(*_args, **_kwargs) -> None:
        return None

    async def fake_preflight(*_args, **_kwargs):
        return {"ok": True, "status": "authoritative", "sources": [old_card], "source_card_count": 1, "source_identities": [old_card["identity"]], "empty_state_visible": False}

    async def fake_upload(*_args, **_kwargs):
        calls["uploads"] += 1

    async def fake_settle(*_args, **_kwargs):
        return {"settled": True}

    async def fake_quiet(*_args, **_kwargs):
        return {"saw_commit": True, "started": 2, "finished": 2, "failed": 0, "inflight": 0}

    async def fake_processing(*_args, **_kwargs):
        return {
            "status": "project_source_processing_stream_completed",
            "assigned_filename": "release(15).zip",
            "library_file_name": "release(15).zip",
            "processed_file_id": processed_file_id,
            "library_metadata_object_id": library_object_id,
        }

    async def fake_snapshot(*_args, **_kwargs):
        return [old_card, new_card]

    async def fail_generic_verify(*_args, **_kwargs):
        calls["generic_verify"] += 1
        raise AssertionError("assigned-name fast verification must skip canonical persistence retries")

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client.ensure_logged_in = fake_noop  # type: ignore[method-assign]
    browser_client._goto = fake_noop  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_noop  # type: ignore[method-assign]
    browser_client._wait_for_authoritative_project_sources_surface = fake_preflight  # type: ignore[method-assign]
    browser_client._add_project_file_source = fake_upload  # type: ignore[method-assign]
    browser_client._wait_for_project_source_post_save_settle = fake_settle  # type: ignore[method-assign]
    browser_client._wait_for_project_source_save_request_quiet = fake_quiet  # type: ignore[method-assign]
    browser_client._wait_for_project_source_processing_stream = fake_processing  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._verify_project_source_persistence = fail_generic_verify  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._install_project_source_save_request_watch = lambda *_args, **_kwargs: {"installed": True, "source_kind": "file", "started": 2, "finished": 2, "failed": 0, "saw_relevant": True, "saw_commit": True, "inflight": set(), "backing_file_ids": [processed_file_id], "backend_assigned_names": ["release.zip", "release(15).zip"]}  # type: ignore[method-assign]
    browser_client._dispose_project_source_save_request_watch = lambda *_args, **_kwargs: None  # type: ignore[method-assign]

    file_path = tmp_path / "release.zip"
    file_path.write_bytes(b"zip")
    result = asyncio.run(browser_client._add_project_source_operation(context=None, page=page, source_kind="file", value=None, file_path=str(file_path), display_name=str(file_path), keep_open=False))

    assert calls == {"uploads": 1, "generic_verify": 0}
    assert result["ok"] is True
    assert result["status"] == "source_added"
    assert result["requested_filename"] == "release.zip"
    assert result["assigned_filename"] == "release(15).zip"
    assert result["previous_max_assigned_index"] == 14
    assert result["expected_next_assigned_index"] == 15
    assert result["assigned_index"] == 15
    assert result["assigned_index_delta"] == 1
    assert result["assigned_index_is_expected_next"] is True
    assert result["pre_upload_family_source_identities"] == ["release(14).zip Document"]
    assert result["canonical_persistence_retry_skipped"] is True

def test_add_file_source_operation_blocks_uncorrelated_indexed_source_after_committed_upload(
    browser_client: ChatGPTBrowserClient,
    tmp_path: Path,
) -> None:
    page = object()
    calls = {"removed": False, "added": False}
    suffix_card = {"identity": "release(1).zip Document", "title": "release(1).zip", "text": "release(1).zip Document"}

    async def fake_noop(*_args, **_kwargs) -> None:
        return None

    preflight_results = [
        {"ok": True, "authoritative": True, "sources": [{"identity": "release.zip Document", "title": "release.zip", "text": "release.zip Document"}], "source_count": 1, "empty_state_visible": False},
        {"ok": True, "authoritative": True, "sources": [], "source_count": 0, "empty_state_visible": True},
    ]

    async def fake_authoritative(*_args, **_kwargs):
        return preflight_results.pop(0)

    async def fake_remove(*_args, **_kwargs):
        calls["removed"] = True
        return {"ok": True, "removed_via_ui": True, "source_match": "release.zip"}

    async def fake_upload(*_args, **_kwargs):
        calls["added"] = True

    async def fake_presence(*_args, **_kwargs):
        raise ResponseTimeoutError("canonical source not visible")

    async def fake_settle(*_args, **_kwargs):
        return {"settled": True}

    async def fake_quiet(*_args, **_kwargs):
        return {"saw_commit": True, "started": 2, "finished": 2, "failed": 0, "inflight": 0}

    async def fake_processing(*_args, **_kwargs):
        return {"status": "completed", "assigned_filename": "release(1).zip", "processed_file_id": None, "library_metadata_object_id": None}

    async def fake_resolution(*_args, **_kwargs):
        return {"ok": True, "sources": [suffix_card], "exact_canonical_sources": [], "duplicate_suffix_sources": [suffix_card]}

    async def fake_safe_url(*_args, **_kwargs):
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    async def fake_exact_assigned(*_args, **_kwargs):
        return {
            "ok": True,
            "status": "exact_assigned_source_verified",
            "requested_filename": "release.zip",
            "assigned_filename": "release(1).zip",
            "assigned_index": 1,
            "source_card": suffix_card,
            "family_sources": [suffix_card],
        }

    browser_client.ensure_logged_in = fake_noop  # type: ignore[method-assign]
    browser_client._goto = fake_noop  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_noop  # type: ignore[method-assign]
    browser_client._wait_for_authoritative_project_sources_surface = fake_authoritative  # type: ignore[method-assign]
    browser_client._remove_project_source_operation = fake_remove  # type: ignore[method-assign]
    browser_client._add_project_file_source = fake_upload  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fake_presence  # type: ignore[method-assign]
    browser_client._wait_for_project_source_post_save_settle = fake_settle  # type: ignore[method-assign]
    browser_client._wait_for_project_source_save_request_quiet = fake_quiet  # type: ignore[method-assign]
    browser_client._wait_for_project_source_processing_stream = fake_processing  # type: ignore[method-assign]
    browser_client._wait_for_post_commit_file_source_resolution = fake_resolution  # type: ignore[method-assign]
    browser_client._wait_for_exact_assigned_file_source = fake_exact_assigned  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_url  # type: ignore[method-assign]
    browser_client._install_project_source_save_request_watch = lambda *_args, **_kwargs: {"installed": True, "source_kind": "file", "started": 2, "finished": 2, "failed": 0, "saw_relevant": True, "saw_commit": True, "inflight": set()}  # type: ignore[method-assign]
    browser_client._dispose_project_source_save_request_watch = lambda *_args, **_kwargs: None  # type: ignore[method-assign]

    file_path = tmp_path / "release.zip"
    file_path.write_bytes(b"zip")
    result = asyncio.run(browser_client._add_project_source_operation(context=None, page=page, source_kind="file", value=None, file_path=str(file_path), display_name=str(file_path), keep_open=False))

    assert calls == {"removed": True, "added": True}
    assert result["ok"] is False
    assert result["status"] == "blocked_ambiguous"
    assert result["conflict_reason"] == "exact_assigned_source_not_correlated_to_current_upload"
    assert result["persistence_verified"] is False
    assert result["project_source_mutated"] is True
    assert result["operator_review_required"] is True
    assert result["indexed_source_correlation"]["status"] == "indexed_source_backend_identity_incomplete"

def test_stale_inflight_post_commit_absent_source_is_classified_as_true_absence(
    browser_client: ChatGPTBrowserClient,
    tmp_path: Path,
) -> None:
    page = object()

    async def fake_ensure_logged_in(*_args, **_kwargs) -> None:
        return None

    async def fake_goto(*_args, **_kwargs) -> None:
        return None

    async def fake_open_sources_tab(*_args, **_kwargs) -> None:
        return None

    async def fake_find_existing(*_args, **_kwargs):
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return [{"identity": "pasted.txt Document", "title": "pasted.txt Document", "text": "pasted.txt Document"}]

    async def fake_add_file_source(*_args, **_kwargs) -> None:
        return None

    async def fake_wait_for_source_presence(*_args, **_kwargs):
        return {"identity": "release.zip", "title": "release.zip", "text": "release.zip Document"}

    async def fake_wait_for_post_save_settle(*_args, **_kwargs):
        return {"settled": True}

    async def fake_wait_for_quiet(*_args, **_kwargs):
        return {
            "saw_commit": True,
            "started": 2,
            "finished": 1,
            "failed": 0,
            "inflight": 1,
            "stale_inflight_after_commit": True,
        }

    async def fake_verify_persistence(*_args, **_kwargs):
        raise ResponseTimeoutError("post-refresh surface did not verify the committed source")

    async def fake_recover(*_args, **_kwargs):
        return None

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_open_sources_tab  # type: ignore[method-assign]
    browser_client._find_existing_file_source_for_overwrite = fake_find_existing  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._add_project_file_source = fake_add_file_source  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fake_wait_for_source_presence  # type: ignore[method-assign]
    browser_client._wait_for_project_source_post_save_settle = fake_wait_for_post_save_settle  # type: ignore[method-assign]
    browser_client._wait_for_project_source_save_request_quiet = fake_wait_for_quiet  # type: ignore[method-assign]
    browser_client._verify_project_source_persistence = fake_verify_persistence  # type: ignore[method-assign]
    browser_client._recover_project_source_after_post_commit_timeout = fake_recover  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._install_project_source_save_request_watch = lambda *_args, **_kwargs: {  # type: ignore[method-assign]
        "installed": True,
        "source_kind": "file",
        "started": 2,
        "finished": 1,
        "failed": 0,
        "saw_relevant": True,
        "saw_commit": True,
        "inflight": {object()},
    }
    browser_client._dispose_project_source_save_request_watch = lambda *_args, **_kwargs: None  # type: ignore[method-assign]

    file_path = tmp_path / "release.zip"
    file_path.write_bytes(b"zip")
    result = asyncio.run(
        browser_client._add_project_source_operation(
            context=None,
            page=page,
            source_kind="file",
            value=None,
            file_path=str(file_path),
            display_name=str(file_path),
            keep_open=False,
        )
    )

    assert result["ok"] is False
    assert result["status"] == "post_commit_source_absent_after_stale_inflight"
    assert result["post_commit_source_absent_after_recovery"] is True
    assert result["post_commit_visible_match_found"] is False
    assert result["current_source_identities"] == ["pasted.txt Document"]


def test_capacity_prune_stops_without_loose_retry_when_exact_remove_reports_identity_drift(
    browser_client: ChatGPTBrowserClient,
    tmp_path: Path,
) -> None:
    page = object()
    release_zip = tmp_path / "chatgpt_claudecode_workflow_v0.0.277.zip"
    release_zip.write_text("fake zip fixture", encoding="utf-8")
    old_source = {
        "title": "chatgpt_claudecode_workflow_v0.0.275.zip",
        "identity": "chatgpt_claudecode_workflow_v0.0.275.zip Document",
        "text": "chatgpt_claudecode_workflow_v0.0.275.zip\nDocument",
        "subtitle": "Document",
    }
    before_sources = [old_source]
    while len(before_sources) < 25:
        index = len(before_sources)
        before_sources.append(
            {
                "title": f"other-source-{index}.txt",
                "identity": f"other-source-{index}.txt Document",
                "text": f"other-source-{index}.txt\nDocument",
                "subtitle": "Document",
            }
        )
    remove_calls: list[bool] = []

    async def fake_ensure_logged_in(*_args, **_kwargs) -> None:
        return None

    async def fake_goto(*_args, **_kwargs) -> None:
        return None

    async def fake_open_sources_tab(*_args, **_kwargs) -> None:
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return list(before_sources)

    async def fake_find_existing(*_args, **_kwargs):
        return None

    async def fake_remove(*_args, **kwargs):
        remove_calls.append(bool(kwargs["exact"]))
        raise ResponseTimeoutError(
            "Project source remove drifted to a different row before the target disappeared "
            "(target=chatgpt_claudecode_workflow_v0.0.275.zip, collateral_removed=['unrelated.txt'])"
        )

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_open_sources_tab  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._find_existing_file_source_for_overwrite = fake_find_existing  # type: ignore[method-assign]
    browser_client._remove_project_source_operation = fake_remove  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]

    result = asyncio.run(
        browser_client._add_project_source_operation(
            context=None,
            page=page,
            source_kind="file",
            value=None,
            file_path=str(release_zip),
            display_name=None,
            keep_open=False,
            protected_release_version="v0.0.276.18",
            protected_release_filename="chatgpt_claudecode_workflow_v0.0.276.18.zip",
        )
    )

    assert remove_calls == [True]
    assert result["ok"] is False
    assert result["status"] == "source_capacity_prune_remove_failed"
    assert result["operator_review_required"] is True
    assert result["capacity_prune_retry_suppressed"] is True
    assert result["capacity_prune_remove_drift_detected"] is True
    assert result["capacity_prune_identity_verified"] is False


def test_open_project_sources_tab_uses_direct_sources_url_without_clicking_escaping_link(browser_client: ChatGPTBrowserClient) -> None:
    browser_client.config.project_url = "https://chatgpt.com/g/g-p-123/project"

    class Page:
        def __init__(self) -> None:
            self.url = "https://chatgpt.com/g/g-p-123/c/conversation-1"
            self.waits: list[int] = []

        async def wait_for_timeout(self, timeout_ms: int) -> None:
            self.waits.append(timeout_ms)

    page = Page()
    calls: list[tuple[str, str]] = []

    async def fake_safe_page_url(target_page) -> str:
        return target_page.url

    async def fake_goto(target_page, url: str, *, label: str, respect_history_rate_limit_cooldown: bool = True) -> None:
        calls.append((label, url))
        target_page.url = url

    async def fail_wait_for_visible(*_args, **_kwargs):
        raise AssertionError("tab lookup/click should be skipped when direct sources URL is active")

    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._wait_for_visible_locator = fail_wait_for_visible  # type: ignore[method-assign]

    asyncio.run(browser_client._open_project_sources_tab(page, project_url="https://chatgpt.com/g/g-p-123/project"))

    assert calls == [
        (
            "project-sources-tab-direct-open",
            "https://chatgpt.com/g/g-p-123/project?tab=sources",
        )
    ]
    assert page.url == "https://chatgpt.com/g/g-p-123/project?tab=sources"


def test_open_project_sources_tab_recovers_if_tab_click_escapes_project_scope(browser_client: ChatGPTBrowserClient) -> None:
    browser_client.config.project_url = "https://chatgpt.com/g/g-p-123/project"

    class Locator:
        async def click(self, timeout: int) -> None:
            page.url = "https://chatgpt.com/c/generic-after-sources-click"

    class Page:
        def __init__(self) -> None:
            self.url = "https://chatgpt.com/g/g-p-123/project?tab=chats"
            self.waits: list[int] = []

        async def wait_for_timeout(self, timeout_ms: int) -> None:
            self.waits.append(timeout_ms)

    page = Page()
    calls: list[tuple[str, str]] = []
    direct_open_done = False

    async def fake_safe_page_url(target_page) -> str:
        return target_page.url

    async def fake_goto(target_page, url: str, *, label: str, respect_history_rate_limit_cooldown: bool = True) -> None:
        nonlocal direct_open_done
        calls.append((label, url))
        target_page.url = url
        if label == "project-sources-tab-direct-open":
            # Simulate a UI that does not honor ?tab=sources, so the tab path is tried.
            target_page.url = "https://chatgpt.com/g/g-p-123/project"
            direct_open_done = True

    async def fake_wait_for_visible(*_args, **kwargs):
        assert kwargs["label"] == "project-sources-tab"
        assert direct_open_done is True
        return Locator()

    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._wait_for_visible_locator = fake_wait_for_visible  # type: ignore[method-assign]

    asyncio.run(browser_client._open_project_sources_tab(page, project_url="https://chatgpt.com/g/g-p-123/project"))

    assert calls == [
        (
            "project-sources-tab-direct-open",
            "https://chatgpt.com/g/g-p-123/project?tab=sources",
        ),
        (
            "project-sources-tab-scope-recovery",
            "https://chatgpt.com/g/g-p-123/project?tab=sources",
        ),
    ]
    assert page.url == "https://chatgpt.com/g/g-p-123/project?tab=sources"


def test_project_source_preflight_zero_cards_without_empty_state_is_not_authoritative(
    browser_client: ChatGPTBrowserClient,
) -> None:
    class Page:
        async def wait_for_timeout(self, _milliseconds: int) -> None:
            await asyncio.sleep(0)

    async def fake_snapshot(*_args, **_kwargs):
        return []

    async def fake_empty(*_args, **_kwargs) -> bool:
        return False

    async def fake_safe_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._project_sources_empty_state_visible = fake_empty  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_url  # type: ignore[method-assign]

    result = asyncio.run(
        browser_client._wait_for_authoritative_project_sources_surface(
            Page(),
            project_url="https://chatgpt.com/g/g-p-123/project",
            label="test-preflight",
            timeout_ms=2,
            poll_interval_ms=0,
        )
    )

    assert result["ok"] is False
    assert result["status"] == "source_preflight_not_authoritative"
    assert result["source_surface_not_ready"] is True
    assert result["source_card_count"] == 0
    assert result["empty_state_visible"] is False



def test_add_file_source_delayed_surface_loading_captures_previous_index_and_uploads_next(browser_client: ChatGPTBrowserClient, tmp_path: Path) -> None:
    class Page:
        async def wait_for_timeout(self, _milliseconds: int) -> None:
            await asyncio.sleep(0)

    old_card = {"identity": "release(4).zip Document", "title": "release(4).zip", "text": "release(4).zip Document"}
    new_card = {"identity": "release(5).zip Document", "title": "release(5).zip", "text": "release(5).zip Document"}
    snapshots = iter([[], [old_card], [old_card]])
    calls = {"uploads": 0}
    processed_file_id = "file_000000001234567890abcdef12345678"
    library_object_id = "libfile_1234567890abcdef1234567890abcdef"

    async def fake_noop(*_args, **_kwargs) -> None:
        return None

    async def fake_snapshot(*_args, **_kwargs):
        try:
            return next(snapshots)
        except StopIteration:
            return [old_card, new_card]

    async def fake_empty(*_args, **_kwargs) -> bool:
        return False

    async def fake_upload(*_args, **_kwargs) -> None:
        calls["uploads"] += 1

    async def fake_settle(*_args, **_kwargs):
        return {"settled": True}

    async def fake_quiet(*_args, **_kwargs):
        return {"saw_commit": True, "started": 2, "finished": 2, "failed": 0, "inflight": 0}

    async def fake_processing(*_args, **_kwargs):
        return {"status": "project_source_processing_stream_completed", "assigned_filename": "release(5).zip", "library_file_name": "release(5).zip", "processed_file_id": processed_file_id, "library_metadata_object_id": library_object_id}

    async def fake_safe_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client.ensure_logged_in = fake_noop  # type: ignore[method-assign]
    browser_client._goto = fake_noop  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_noop  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._project_sources_empty_state_visible = fake_empty  # type: ignore[method-assign]
    browser_client._add_project_file_source = fake_upload  # type: ignore[method-assign]
    browser_client._wait_for_project_source_post_save_settle = fake_settle  # type: ignore[method-assign]
    browser_client._wait_for_project_source_save_request_quiet = fake_quiet  # type: ignore[method-assign]
    browser_client._wait_for_project_source_processing_stream = fake_processing  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_url  # type: ignore[method-assign]
    browser_client._install_project_source_save_request_watch = lambda *_args, **_kwargs: {"installed": True, "source_kind": "file", "started": 2, "finished": 2, "failed": 0, "saw_relevant": True, "saw_commit": True, "inflight": set(), "backing_file_ids": [processed_file_id], "backend_assigned_names": ["release(5).zip"]}  # type: ignore[method-assign]
    browser_client._dispose_project_source_save_request_watch = lambda *_args, **_kwargs: None  # type: ignore[method-assign]

    file_path = tmp_path / "release.zip"
    file_path.write_bytes(b"zip")
    result = asyncio.run(browser_client._add_project_source_operation(context=None, page=Page(), source_kind="file", value=None, file_path=str(file_path), display_name=str(file_path), keep_open=False))

    assert calls["uploads"] == 1
    assert result["ok"] is True
    assert result["previous_max_assigned_index"] == 4
    assert result["assigned_index"] == 5
    assert result["assigned_index_is_expected_next"] is True

def test_source_add_accepts_correlated_indexed_assigned_filename(
    browser_client: ChatGPTBrowserClient,
    tmp_path: Path,
) -> None:
    page = object()
    calls = {"uploaded": False, "verified": False}
    suffix_card = {"identity": "release(14).zip Document", "title": "release(14).zip", "text": "release(14).zip Document"}
    processed_file_id = "file_000000001234567890abcdef12345678"
    library_object_id = "libfile_1234567890abcdef1234567890abcdef"

    async def fake_noop(*_args, **_kwargs) -> None:
        return None

    async def fake_preflight(*_args, **_kwargs):
        return {"ok": True, "status": "authoritative_empty", "sources": [], "source_card_count": 0, "source_identities": [], "empty_state_visible": True}

    async def fake_find_existing(*_args, **_kwargs):
        return None

    async def fake_upload(*_args, **_kwargs):
        calls["uploaded"] = True

    async def fake_presence(*_args, **_kwargs):
        raise ResponseTimeoutError("canonical source not visible yet")

    async def fake_settle(*_args, **_kwargs):
        return {"settled": True}

    async def fake_quiet(*_args, **_kwargs):
        return {"saw_commit": True, "started": 2, "finished": 2, "failed": 0, "inflight": 0}

    async def fake_processing(*_args, **_kwargs):
        return {
            "status": "project_source_processing_stream_completed",
            "assigned_filename": "release(14).zip",
            "library_file_name": "release(14).zip",
            "processed_file_id": processed_file_id,
            "library_metadata_object_id": library_object_id,
            "filename_correlation": "backend_assigned_indexed",
            "identity_verified": True,
        }

    async def fake_resolution(*_args, **_kwargs):
        return {"ok": True, "status": "backend_assigned_indexed_source_visible", "sources": [suffix_card], "exact_canonical_sources": [], "duplicate_suffix_sources": [suffix_card]}

    async def fake_verify(*_args, **_kwargs):
        calls["verified"] = True
        return dict(suffix_card)

    async def fake_snapshot(*_args, **_kwargs):
        return [suffix_card]

    async def fake_safe_url(*_args, **_kwargs):
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client.ensure_logged_in = fake_noop  # type: ignore[method-assign]
    browser_client._goto = fake_noop  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_noop  # type: ignore[method-assign]
    browser_client._wait_for_authoritative_project_sources_surface = fake_preflight  # type: ignore[method-assign]
    browser_client._find_existing_file_source_for_overwrite = fake_find_existing  # type: ignore[method-assign]
    browser_client._add_project_file_source = fake_upload  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fake_presence  # type: ignore[method-assign]
    browser_client._wait_for_project_source_post_save_settle = fake_settle  # type: ignore[method-assign]
    browser_client._wait_for_project_source_save_request_quiet = fake_quiet  # type: ignore[method-assign]
    browser_client._wait_for_project_source_processing_stream = fake_processing  # type: ignore[method-assign]
    browser_client._wait_for_post_commit_file_source_resolution = fake_resolution  # type: ignore[method-assign]
    browser_client._verify_project_source_persistence = fake_verify  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_url  # type: ignore[method-assign]
    browser_client._install_project_source_save_request_watch = lambda *_args, **_kwargs: {"installed": True, "source_kind": "file", "started": 2, "finished": 2, "failed": 0, "saw_relevant": True, "saw_commit": True, "inflight": set(), "backing_file_ids": [processed_file_id], "backend_assigned_names": ["release(14).zip"]}  # type: ignore[method-assign]
    browser_client._dispose_project_source_save_request_watch = lambda *_args, **_kwargs: None  # type: ignore[method-assign]

    file_path = tmp_path / "release.zip"
    file_path.write_bytes(b"zip")
    result = asyncio.run(browser_client._add_project_source_operation(context=None, page=page, source_kind="file", value=None, file_path=str(file_path), display_name=str(file_path), keep_open=False))

    assert calls == {"uploaded": True, "verified": False}
    assert result["ok"] is True
    assert result["status"] == "source_added"
    assert result["requested_filename"] == "release.zip"
    assert result["assigned_filename"] == "release(14).zip"
    assert result["processed_file_id"] == processed_file_id
    assert result["library_metadata_object_id"] == library_object_id
    assert result["project_source_mutated"] is True
    assert result["persistence_verified"] is True
    assert result["operator_review_required"] is False
    assert result["indexed_source_correlation"]["status"] == "current_upload_correlated_assigned_source"
    assert result["verification_mode"] == "processing_stream_assigned_filename_exact"
    assert result["canonical_persistence_retry_skipped"] is True
    assert result["duplicate_suffix_source_count"] == 1

def _library_surface(records, *, reason: str = "stable_library_snapshot"):
    family_records = list(records)
    return {
        "ok": True,
        "authoritative": True,
        "reason": reason,
        "records": list(records),
        "family_records": family_records,
        "record_count": len(records),
        "family_record_count": len(family_records),
        "empty_state_visible": not records,
        "stable_observations": 2 if records else 0,
        "observations": [],
    }


def _install_library_surface_sequence(browser_client: ChatGPTBrowserClient, surfaces: list[dict]) -> None:
    async def fake_surface(*_args, **_kwargs):
        assert surfaces, "unexpected Library authority probe"
        return surfaces.pop(0)

    browser_client._wait_for_authoritative_library_family_surface = fake_surface  # type: ignore[method-assign]


def test_library_filename_family_matches_exact_and_numeric_suffixes(browser_client: ChatGPTBrowserClient) -> None:
    canonical = "platform-gitops_v0.0.6.6.zip"
    assert browser_client._file_source_family_member(canonical, canonical) is True
    assert browser_client._file_source_family_member("platform-gitops_v0.0.6.6(7).zip", canonical) is True
    assert browser_client._file_source_family_member("platform-gitops_v0.0.6.6 (7).zip", canonical) is True
    assert browser_client._file_source_family_member("platform-gitops_v0.0.6.60.zip", canonical) is False
    assert browser_client._file_source_family_member("other(7).zip", canonical) is False


def test_upload_response_extracts_backing_file_id_and_backend_assigned_name(browser_client: ChatGPTBrowserClient) -> None:
    payload = {
        "upload": {
            "file_id": "file_1234567890abcdef",
            "filename": "platform-gitops_v0.0.6.6(7).zip",
            "project_id": "g-p-current",
        }
    }
    records = browser_client._extract_library_file_records_from_payload(
        payload,
        source_url="https://chatgpt.com/backend-api/files/process_upload_stream",
    )
    assert records == [
        {
            "file_id": "file_1234567890abcdef",
            "filename": "platform-gitops_v0.0.6.6(7).zip",
            "project_ids": ["g-p-current"],
            "project_references_known": True,
            "deleted": False,
            "source_url": "https://chatgpt.com/backend-api/files/process_upload_stream",
        }
    ]


def test_library_transaction_ledger_attributes_prior_promptbranch_upload(
    browser_client: ChatGPTBrowserClient,
) -> None:
    browser_client._record_library_upload_transactions(
        project_url="https://chatgpt.com/g/g-p-current/project",
        canonical_name="release.zip",
        file_ids=["file_ledger_123456"],
        assigned_names=["release(2).zip"],
    )
    assert browser_client._library_transaction_ids_for_family(
        "release.zip",
        "https://chatgpt.com/g/g-p-current/project",
    ) == {"file_ledger_123456"}
    assert browser_client._library_transaction_ids_for_family(
        "release.zip",
        "https://chatgpt.com/g/g-p-other/project",
    ) == set()
    browser_client._forget_library_upload_transactions(["file_ledger_123456"])
    assert browser_client._library_transaction_ids_for_family(
        "release.zip",
        "https://chatgpt.com/g/g-p-current/project",
    ) == set()


class _LibraryWatchContext:
    def __init__(self) -> None:
        self.handlers: dict[str, object] = {}

    def on(self, event_name: str, handler) -> None:
        self.handlers[event_name] = handler

    def remove_listener(self, event_name: str, handler) -> None:
        if self.handlers.get(event_name) is handler:
            self.handlers.pop(event_name, None)


class _LibraryPage:
    url = "https://chatgpt.com/library"

    async def wait_for_timeout(self, _milliseconds: int) -> None:
        return None


def _library_surface(records, *, reason: str = "stable_library_snapshot"):
    family_records = list(records)
    return {
        "ok": True,
        "authoritative": True,
        "reason": reason,
        "records": list(records),
        "family_records": family_records,
        "record_count": len(records),
        "family_record_count": len(family_records),
        "empty_state_visible": not records,
        "stable_observations": 2 if records else 0,
        "observations": [],
    }


def _install_library_surface_sequence(browser_client: ChatGPTBrowserClient, surfaces: list[dict]) -> None:
    async def fake_surface(*_args, **_kwargs):
        assert surfaces, "unexpected Library authority probe"
        return surfaces.pop(0)

    browser_client._wait_for_authoritative_library_family_surface = fake_surface  # type: ignore[method-assign]


def test_library_filename_family_matches_exact_and_numeric_suffixes(browser_client: ChatGPTBrowserClient) -> None:
    canonical = "platform-gitops_v0.0.6.6.zip"
    assert browser_client._file_source_family_member(canonical, canonical) is True
    assert browser_client._file_source_family_member("platform-gitops_v0.0.6.6(7).zip", canonical) is True
    assert browser_client._file_source_family_member("platform-gitops_v0.0.6.6 (7).zip", canonical) is True
    assert browser_client._file_source_family_member("platform-gitops_v0.0.6.60.zip", canonical) is False
    assert browser_client._file_source_family_member("other(7).zip", canonical) is False


def test_upload_response_extracts_backing_file_id_and_backend_assigned_name(browser_client: ChatGPTBrowserClient) -> None:
    payload = {
        "upload": {
            "file_id": "file_1234567890abcdef",
            "filename": "platform-gitops_v0.0.6.6(7).zip",
            "project_id": "g-p-current",
        }
    }
    records = browser_client._extract_library_file_records_from_payload(
        payload,
        source_url="https://chatgpt.com/backend-api/files/process_upload_stream",
    )
    assert records == [
        {
            "file_id": "file_1234567890abcdef",
            "filename": "platform-gitops_v0.0.6.6(7).zip",
            "project_ids": ["g-p-current"],
            "project_references_known": True,
            "deleted": False,
            "source_url": "https://chatgpt.com/backend-api/files/process_upload_stream",
        }
    ]


def test_library_transaction_ledger_attributes_prior_promptbranch_upload(
    browser_client: ChatGPTBrowserClient,
) -> None:
    browser_client._record_library_upload_transactions(
        project_url="https://chatgpt.com/g/g-p-current/project",
        canonical_name="release.zip",
        file_ids=["file_ledger_123456"],
        assigned_names=["release(2).zip"],
    )
    assert browser_client._library_transaction_ids_for_family(
        "release.zip",
        "https://chatgpt.com/g/g-p-current/project",
    ) == {"file_ledger_123456"}
    assert browser_client._library_transaction_ids_for_family(
        "release.zip",
        "https://chatgpt.com/g/g-p-other/project",
    ) == set()
    browser_client._forget_library_upload_transactions(["file_ledger_123456"])
    assert browser_client._library_transaction_ids_for_family(
        "release.zip",
        "https://chatgpt.com/g/g-p-current/project",
    ) == set()


def test_library_reconciliation_accepts_exact_required_file_id_when_reference_metadata_is_unknown(
    browser_client: ChatGPTBrowserClient,
) -> None:
    context = _LibraryWatchContext()
    page = _LibraryPage()
    snapshots = [
        [{"file_id": "file_required_123", "filename": "release.zip", "project_ids": [], "project_references_known": False, "deleted": False}],
        [{"file_id": "file_required_123", "filename": "release.zip", "project_ids": [], "project_references_known": False, "deleted": True}],
        [],
        [],
    ]
    actions: list[tuple[str, bool]] = []
    active_record = snapshots[0][0]
    deleted_record = snapshots[1][0]
    surfaces = [
        _library_surface([active_record]),
        _library_surface([]),
        _library_surface([active_record]),
        _library_surface([deleted_record]),
        _library_surface([]),
        _library_surface([]),
    ]

    async def fake_noop(*_args, **_kwargs) -> None:
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return snapshots.pop(0)

    async def fake_delete(_page, *, file_id: str, filename: str, delete_forever: bool):
        actions.append((file_id, delete_forever))
        return {"ok": True}

    browser_client._goto = fake_noop  # type: ignore[method-assign]
    browser_client._library_search_exact_family = fake_noop  # type: ignore[method-assign]
    browser_client._snapshot_library_file_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._delete_library_file_record_via_ui = fake_delete  # type: ignore[method-assign]
    browser_client._open_library_recently_deleted = lambda *_args, **_kwargs: asyncio.sleep(0, result=True)  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_noop  # type: ignore[method-assign]
    _install_library_surface_sequence(browser_client, surfaces)

    result = asyncio.run(
        browser_client._reconcile_library_file_family(
            context=context,
            page=page,
            project_url="https://chatgpt.com/g/g-p-current/project",
            canonical_name="release.zip",
            required_file_ids=["file_required_123"],
        )
    )

    assert result["ok"] is True
    assert actions == [("file_required_123", False), ("file_required_123", True)]


def test_library_reconciliation_deletes_retained_file_and_recently_deleted_entry(
    browser_client: ChatGPTBrowserClient,
) -> None:
    context = _LibraryWatchContext()
    page = _LibraryPage()
    snapshots = [
        [{"file_id": "file_retained_123", "filename": "release.zip", "project_ids": [], "project_references_known": True, "deleted": False}],
        [{"file_id": "file_retained_123", "filename": "release.zip", "project_ids": [], "project_references_known": True, "deleted": True}],
        [],
        [],
    ]
    actions: list[tuple[str, bool]] = []
    active_record = snapshots[0][0]
    deleted_record = snapshots[1][0]
    surfaces = [
        _library_surface([active_record]),
        _library_surface([]),
        _library_surface([active_record]),
        _library_surface([deleted_record]),
        _library_surface([]),
        _library_surface([]),
    ]

    async def fake_goto(*_args, **_kwargs) -> None:
        return None

    async def fake_search(*_args, **_kwargs) -> None:
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return snapshots.pop(0)

    async def fake_delete(_page, *, file_id: str, filename: str, delete_forever: bool):
        actions.append((file_id, delete_forever))
        return {"ok": True, "status": "delete_forever_triggered" if delete_forever else "delete_triggered"}

    async def fake_recent(*_args, **_kwargs) -> bool:
        return True

    browser_client._goto = fake_goto  # type: ignore[method-assign]
    browser_client._library_search_exact_family = fake_search  # type: ignore[method-assign]
    browser_client._snapshot_library_file_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._delete_library_file_record_via_ui = fake_delete  # type: ignore[method-assign]
    browser_client._open_library_recently_deleted = fake_recent  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_goto  # type: ignore[method-assign]
    _install_library_surface_sequence(browser_client, surfaces)

    result = asyncio.run(
        browser_client._reconcile_library_file_family(
            context=context,
            page=page,
            project_url="https://chatgpt.com/g/g-p-current/project",
            canonical_name="release.zip",
        )
    )

    assert result["ok"] is True
    assert result["status"] == "library_collision_cleared"
    assert actions == [("file_retained_123", False), ("file_retained_123", True)]
    assert result["remaining_records"] == []


def test_library_reconciliation_clears_polluted_numeric_suffix_history(
    browser_client: ChatGPTBrowserClient,
) -> None:
    context = _LibraryWatchContext()
    page = _LibraryPage()
    family = [
        {"file_id": "file_family_000", "filename": "release.zip", "project_ids": [], "project_references_known": True, "deleted": False},
        {"file_id": "file_family_001", "filename": "release(1).zip", "project_ids": [], "project_references_known": True, "deleted": False},
        {"file_id": "file_family_002", "filename": "release (2).zip", "project_ids": [], "project_references_known": True, "deleted": False},
    ]
    snapshots = [family, [{**item, "deleted": True} for item in family], [], []]
    actions: list[tuple[str, bool]] = []
    deleted_family = [{**item, "deleted": True} for item in family]
    surfaces = [
        _library_surface(family),
        _library_surface([]),
        _library_surface(family),
        _library_surface(deleted_family),
        _library_surface([]),
        _library_surface([]),
    ]

    async def fake_noop(*_args, **_kwargs) -> None:
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return snapshots.pop(0)

    async def fake_delete(_page, *, file_id: str, filename: str, delete_forever: bool):
        actions.append((file_id, delete_forever))
        return {"ok": True}

    browser_client._goto = fake_noop  # type: ignore[method-assign]
    browser_client._library_search_exact_family = fake_noop  # type: ignore[method-assign]
    browser_client._snapshot_library_file_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._delete_library_file_record_via_ui = fake_delete  # type: ignore[method-assign]
    browser_client._open_library_recently_deleted = lambda *_args, **_kwargs: asyncio.sleep(0, result=True)  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_noop  # type: ignore[method-assign]
    _install_library_surface_sequence(browser_client, surfaces)

    result = asyncio.run(
        browser_client._reconcile_library_file_family(
            context=context,
            page=page,
            project_url="https://chatgpt.com/g/g-p-current/project",
            canonical_name="release.zip",
        )
    )

    assert result["ok"] is True
    assert len(result["deleted_records"]) == 3
    assert actions == [
        ("file_family_000", False),
        ("file_family_001", False),
        ("file_family_002", False),
        ("file_family_000", True),
        ("file_family_001", True),
        ("file_family_002", True),
    ]


def test_library_reconciliation_blocks_file_referenced_by_other_project(
    browser_client: ChatGPTBrowserClient,
) -> None:
    context = _LibraryWatchContext()
    page = _LibraryPage()
    deleted = {"called": False}
    shared_record = {
        "file_id": "file_shared_123",
        "filename": "release.zip",
        "project_ids": ["g-p-other"],
        "project_references_known": True,
        "deleted": False,
    }
    surfaces = [_library_surface([shared_record]), _library_surface([])]

    async def fake_noop(*_args, **_kwargs) -> None:
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return [shared_record]

    async def fake_delete(*_args, **_kwargs):
        deleted["called"] = True
        return {"ok": True}

    browser_client._goto = fake_noop  # type: ignore[method-assign]
    browser_client._library_search_exact_family = fake_noop  # type: ignore[method-assign]
    browser_client._snapshot_library_file_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._delete_library_file_record_via_ui = fake_delete  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_noop  # type: ignore[method-assign]
    browser_client._open_library_recently_deleted = lambda *_args, **_kwargs: asyncio.sleep(0, result=True)  # type: ignore[method-assign]
    _install_library_surface_sequence(browser_client, surfaces)

    result = asyncio.run(
        browser_client._reconcile_library_file_family(
            context=context,
            page=page,
            project_url="https://chatgpt.com/g/g-p-current/project",
            canonical_name="release.zip",
        )
    )

    assert result["ok"] is False
    assert result["status"] == "library_collision_ambiguous"
    assert result["release_blocking"] is True
    assert deleted["called"] is False
    assert result["ambiguous_records"][0]["reason"] == "referenced_by_other_project"


def test_library_payload_does_not_misclassify_project_id_as_file_id(browser_client: ChatGPTBrowserClient) -> None:
    records = browser_client._extract_library_file_records_from_payload({
        "id": "g-p-project123",
        "filename": "release.zip",
        "project_ids": [],
        "type": "project_source",
    })
    assert records == []


def test_upload_stream_ndjson_extracts_file_id_and_assigned_name(browser_client: ChatGPTBrowserClient) -> None:
    body = "event: upload\n" + 'data: {"upload":{"file_id":"file_stream_123456","filename":"release(3).zip","project_ids":[]}}\n' + "data: [DONE]\n"
    records = browser_client._extract_library_file_records_from_text(
        body,
        source_url="https://chatgpt.com/backend-api/files/process_upload_stream",
    )
    assert len(records) == 1
    assert records[0]["file_id"] == "file_stream_123456"
    assert records[0]["filename"] == "release(3).zip"
    assert records[0]["project_references_known"] is True


def test_library_reconciliation_blocks_unknown_reference_ownership(
    browser_client: ChatGPTBrowserClient,
) -> None:
    context = _LibraryWatchContext()
    page = _LibraryPage()
    deleted = {"called": False}
    unknown_record = {
        "file_id": "file_unknown_123",
        "filename": "release.zip",
        "project_ids": [],
        "project_references_known": False,
        "deleted": False,
    }
    surfaces = [_library_surface([unknown_record]), _library_surface([])]

    async def fake_noop(*_args, **_kwargs) -> None:
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return [unknown_record]

    async def fake_delete(*_args, **_kwargs):
        deleted["called"] = True
        return {"ok": True}

    browser_client._goto = fake_noop  # type: ignore[method-assign]
    browser_client._library_search_exact_family = fake_noop  # type: ignore[method-assign]
    browser_client._snapshot_library_file_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._delete_library_file_record_via_ui = fake_delete  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_noop  # type: ignore[method-assign]
    browser_client._open_library_recently_deleted = lambda *_args, **_kwargs: asyncio.sleep(0, result=True)  # type: ignore[method-assign]
    _install_library_surface_sequence(browser_client, surfaces)

    result = asyncio.run(
        browser_client._reconcile_library_file_family(
            context=context,
            page=page,
            project_url="https://chatgpt.com/g/g-p-current/project",
            canonical_name="release.zip",
        )
    )

    assert result["ok"] is False
    assert result["status"] == "library_collision_ambiguous"
    assert result["ambiguous_records"][0]["reason"] == "library_file_ownership_not_proven"
    assert deleted["called"] is False


def test_library_reconciliation_requires_exact_file_id(browser_client: ChatGPTBrowserClient) -> None:
    context = _LibraryWatchContext()
    page = _LibraryPage()
    missing_id_record = {"file_id": "", "filename": "release.zip", "project_ids": [], "project_references_known": True, "deleted": False}
    surfaces = [_library_surface([missing_id_record]), _library_surface([])]

    async def fake_noop(*_args, **_kwargs) -> None:
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return [missing_id_record]

    browser_client._goto = fake_noop  # type: ignore[method-assign]
    browser_client._library_search_exact_family = fake_noop  # type: ignore[method-assign]
    browser_client._snapshot_library_file_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_noop  # type: ignore[method-assign]
    browser_client._open_library_recently_deleted = lambda *_args, **_kwargs: asyncio.sleep(0, result=True)  # type: ignore[method-assign]
    _install_library_surface_sequence(browser_client, surfaces)

    result = asyncio.run(
        browser_client._reconcile_library_file_family(
            context=context,
            page=page,
            project_url="https://chatgpt.com/g/g-p-current/project",
            canonical_name="release.zip",
        )
    )

    assert result["ok"] is False
    assert result["status"] == "library_collision_ambiguous"
    assert result["ambiguous_records"][0]["reason"] == "missing_file_id"


def test_library_surface_waits_for_stable_delayed_records(
    browser_client: ChatGPTBrowserClient,
) -> None:
    page = _LibraryPage()
    record = {
        "file_id": "file_delayed_123",
        "filename": "release.zip",
        "project_ids": [],
        "project_references_known": True,
        "deleted": False,
    }
    snapshots = [[], [], [record], [record]]

    async def fake_snapshot(*_args, **_kwargs):
        return snapshots.pop(0)

    async def fake_empty(*_args, **_kwargs) -> bool:
        return False

    browser_client._snapshot_library_file_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._library_empty_state_visible = fake_empty  # type: ignore[method-assign]

    result = asyncio.run(
        browser_client._wait_for_authoritative_library_family_surface(
            page,
            canonical_name="release.zip",
            label="test-delayed-library",
            timeout_ms=2_000,
            poll_ms=1,
        )
    )

    assert result["ok"] is True
    assert result["reason"] == "stable_library_snapshot"
    assert result["family_records"] == [record]
    assert len(result["observations"]) == 4


def test_library_surface_zero_without_empty_state_is_not_authoritative(
    browser_client: ChatGPTBrowserClient,
) -> None:
    class _TimedPage:
        async def wait_for_timeout(self, milliseconds: int) -> None:
            await asyncio.sleep(milliseconds / 1000)

    page = _TimedPage()

    async def fake_snapshot(*_args, **_kwargs):
        return []

    async def fake_empty(*_args, **_kwargs) -> bool:
        return False

    browser_client._snapshot_library_file_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._library_empty_state_visible = fake_empty  # type: ignore[method-assign]

    result = asyncio.run(
        browser_client._wait_for_authoritative_library_family_surface(
            page,
            canonical_name="release.zip",
            label="test-not-authoritative",
            timeout_ms=3,
            poll_ms=1,
        )
    )

    assert result["ok"] is False
    assert result["reason"] == "library_surface_not_authoritative"
    assert result["record_count"] == 0


def test_library_reconciliation_accepts_file_referenced_only_by_target_project(
    browser_client: ChatGPTBrowserClient,
) -> None:
    context = _LibraryWatchContext()
    page = _LibraryPage()
    active = {
        "file_id": "file_target_123",
        "filename": "release.zip",
        "project_ids": ["g-p-current"],
        "project_references_known": True,
        "deleted": False,
    }
    deleted = {**active, "project_ids": [], "deleted": True}
    surfaces = [
        _library_surface([active]),
        _library_surface([]),
        _library_surface([active]),
        _library_surface([deleted]),
        _library_surface([]),
        _library_surface([]),
    ]
    actions: list[tuple[str, bool]] = []

    async def fake_noop(*_args, **_kwargs) -> None:
        return None

    async def fake_delete(_page, *, file_id: str, filename: str, delete_forever: bool):
        actions.append((file_id, delete_forever))
        return {"ok": True}

    browser_client._goto = fake_noop  # type: ignore[method-assign]
    browser_client._library_search_exact_family = fake_noop  # type: ignore[method-assign]
    browser_client._delete_library_file_record_via_ui = fake_delete  # type: ignore[method-assign]
    browser_client._open_library_recently_deleted = lambda *_args, **_kwargs: asyncio.sleep(0, result=True)  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_noop  # type: ignore[method-assign]
    _install_library_surface_sequence(browser_client, surfaces)

    result = asyncio.run(
        browser_client._reconcile_library_file_family(
            context=context,
            page=page,
            project_url="https://chatgpt.com/g/g-p-current/project",
            canonical_name="release.zip",
        )
    )

    assert result["ok"] is True
    assert actions == [("file_target_123", False), ("file_target_123", True)]


def test_library_reconciliation_hard_deletes_preexisting_recently_deleted_collision(
    browser_client: ChatGPTBrowserClient,
) -> None:
    context = _LibraryWatchContext()
    page = _LibraryPage()
    deleted = {
        "file_id": "file_deleted_123",
        "filename": "release(4).zip",
        "project_ids": [],
        "project_references_known": True,
        "deleted": True,
    }
    surfaces = [
        _library_surface([]),
        _library_surface([deleted]),
        _library_surface([deleted]),
        _library_surface([]),
        _library_surface([]),
    ]
    actions: list[tuple[str, bool]] = []

    async def fake_noop(*_args, **_kwargs) -> None:
        return None

    async def fake_delete(_page, *, file_id: str, filename: str, delete_forever: bool):
        actions.append((file_id, delete_forever))
        return {"ok": True}

    browser_client._goto = fake_noop  # type: ignore[method-assign]
    browser_client._library_search_exact_family = fake_noop  # type: ignore[method-assign]
    browser_client._delete_library_file_record_via_ui = fake_delete  # type: ignore[method-assign]
    browser_client._open_library_recently_deleted = lambda *_args, **_kwargs: asyncio.sleep(0, result=True)  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_noop  # type: ignore[method-assign]
    _install_library_surface_sequence(browser_client, surfaces)

    result = asyncio.run(
        browser_client._reconcile_library_file_family(
            context=context,
            page=page,
            project_url="https://chatgpt.com/g/g-p-current/project",
            canonical_name="release.zip",
        )
    )

    assert result["ok"] is True
    assert actions == [("file_deleted_123", True)]
    assert result["deleted_records"][0]["soft_delete"]["status"] == "already_in_recently_deleted"


def test_library_delete_locator_never_falls_back_to_filename_only(
    browser_client: ChatGPTBrowserClient,
) -> None:
    class _MissingIdLocator:
        @property
        def first(self):
            return self

        async def count(self) -> int:
            return 0

    class _Page:
        def locator(self, _selector: str):
            return _MissingIdLocator()

        def get_by_text(self, *_args, **_kwargs):
            raise AssertionError("filename-only Library deletion fallback must not be used")

    result = asyncio.run(
        browser_client._find_exact_library_file_locator(
            _Page(),
            file_id="file_exact_123456",
            filename="release.zip",
        )
    )

    assert result is None



def test_library_surface_stable_empty_requires_two_observations(
    browser_client: ChatGPTBrowserClient,
) -> None:
    page = _LibraryPage()
    calls = {"snapshot": 0, "empty": 0}

    async def fake_snapshot(*_args, **_kwargs):
        calls["snapshot"] += 1
        return []

    async def fake_empty(*_args, **_kwargs) -> bool:
        calls["empty"] += 1
        return True

    browser_client._snapshot_library_file_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._library_empty_state_visible = fake_empty  # type: ignore[method-assign]

    result = asyncio.run(
        browser_client._wait_for_authoritative_library_family_surface(
            page,
            canonical_name="release.zip",
            label="stable-empty",
            timeout_ms=1_000,
            poll_ms=1,
            required_stable_observations=2,
        )
    )

    assert result["ok"] is True
    assert result["reason"] == "stable_explicit_empty_state"
    assert result["stable_observations"] == 2
    assert calls == {"snapshot": 2, "empty": 2}


def test_library_surface_transient_empty_followed_by_records_is_not_accepted(
    browser_client: ChatGPTBrowserClient,
) -> None:
    page = _LibraryPage()
    record = {
        "file_id": "file_after_empty_123456",
        "filename": "release.zip",
        "project_ids": [],
        "project_references_known": True,
        "deleted": False,
    }
    snapshots = [[], [record], [record]]
    empty_states = [True, False, False]

    async def fake_snapshot(*_args, **_kwargs):
        return snapshots.pop(0)

    async def fake_empty(*_args, **_kwargs) -> bool:
        return empty_states.pop(0)

    browser_client._snapshot_library_file_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._library_empty_state_visible = fake_empty  # type: ignore[method-assign]

    result = asyncio.run(
        browser_client._wait_for_authoritative_library_family_surface(
            page,
            canonical_name="release.zip",
            label="transient-empty",
            timeout_ms=1_000,
            poll_ms=1,
        )
    )

    assert result["ok"] is True
    assert result["reason"] == "stable_library_snapshot"
    assert result["family_records"] == [record]
    assert len(result["observations"]) == 3


def test_library_reconciliation_recently_deleted_unavailable_fails_closed(
    browser_client: ChatGPTBrowserClient,
) -> None:
    context = _LibraryWatchContext()
    page = _LibraryPage()

    async def fake_noop(*_args, **_kwargs) -> None:
        return None

    async def fake_surface(*_args, **_kwargs):
        return _library_surface([])

    browser_client._goto = fake_noop  # type: ignore[method-assign]
    browser_client._library_search_exact_family = fake_noop  # type: ignore[method-assign]
    browser_client._wait_for_authoritative_library_family_surface = fake_surface  # type: ignore[method-assign]
    browser_client._open_library_recently_deleted = lambda *_args, **_kwargs: asyncio.sleep(0, result=False)  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_noop  # type: ignore[method-assign]

    result = asyncio.run(
        browser_client._reconcile_library_file_family(
            context=context,
            page=page,
            project_url="https://chatgpt.com/g/g-p-current/project",
            canonical_name="release.zip",
        )
    )

    assert result["ok"] is False
    assert result["status"] == "library_recently_deleted_not_authoritative"
    assert result["release_blocking"] is True
    assert result["deleted_surface"]["authoritative"] is False


def test_production_upload_json_without_filename_uses_expected_canonical_name(
    browser_client: ChatGPTBrowserClient,
) -> None:
    body = '{"status":"success","result":{"upload":{"file_id":"file-live-prod-123456789"}}}'
    records = browser_client._extract_upload_response_records(
        body=body,
        source_url="https://chatgpt.com/backend-api/files/process_upload_stream",
        headers={"content-type": "application/json"},
        expected_filename="release.zip",
    )
    assert records == [{
        "file_id": "file-live-prod-123456789",
        "filename": "release.zip",
        "project_ids": [],
        "project_references_known": False,
        "deleted": False,
        "source_url": "https://chatgpt.com/backend-api/files/process_upload_stream",
    }]


def test_streaming_upload_response_without_filename_captures_expected_name(
    browser_client: ChatGPTBrowserClient,
) -> None:
    body = 'event: upload\ndata: {"result":{"file":{"id":"file-stream-live-123456789","type":"file"}}}\ndata: [DONE]\n'
    records = browser_client._extract_upload_response_records(
        body=body,
        source_url="https://chatgpt.com/backend-api/files/process_upload_stream",
        headers={"content-type": "text/event-stream"},
        expected_filename="release.zip",
    )
    assert [(record["file_id"], record["filename"]) for record in records] == [
        ("file-stream-live-123456789", "release.zip")
    ]


def test_upload_identity_can_be_captured_from_location_header(
    browser_client: ChatGPTBrowserClient,
) -> None:
    records = browser_client._extract_upload_response_records(
        body="",
        source_url="https://chatgpt.com/backend-api/files/process_upload_stream",
        headers={
            "content-type": "application/json",
            "location": "https://chatgpt.com/backend-api/files/file-header-123456789",
            "content-disposition": 'attachment; filename="release(4).zip"',
        },
        expected_filename="release.zip",
    )
    assert [(record["file_id"], record["filename"]) for record in records] == [
        ("file-header-123456789", "release(4).zip")
    ]


def test_save_watch_persists_bounded_upload_response_diagnostics(
    browser_client: ChatGPTBrowserClient,
) -> None:
    context = _LibraryWatchContext()

    class Response:
        url = "https://chatgpt.com/backend-api/files/process_upload_stream"
        status = 200

        async def text(self) -> str:
            return '{"status":"success","file_id":"file-diagnostic-123456789"}'

        async def all_headers(self):
            return {"content-type": "application/json"}

    async def run():
        watch = browser_client._install_project_source_save_request_watch(
            context,
            source_kind="file",
            expected_filename="release.zip",
        )
        context.handlers["response"](Response())
        await asyncio.gather(*watch["response_tasks"])
        return browser_client._project_source_save_watch_summary(watch)

    summary = asyncio.run(run())
    assert summary["backing_file_ids"] == ["file-diagnostic-123456789"]
    assert summary["backend_assigned_names"] == ["release.zip"]
    assert summary["backing_file_identity_captured"] is True
    diagnostic = summary["response_diagnostics"][0]
    assert diagnostic["status"] == 200
    assert diagnostic["content_type"] == "application/json"
    assert diagnostic["body_schema"]["format"] == "json"
    assert diagnostic["extracted_file_ids"] == ["file-diagnostic-123456789"]
    assert diagnostic["extracted_filenames"] == ["release.zip"]
    assert len(diagnostic["body_sample"]) <= 2048



def test_existing_indexed_source_correlation_verifies_library_ids_and_size(
    browser_client: ChatGPTBrowserClient,
    tmp_path: Path,
) -> None:
    class Context:
        def on(self, *_args, **_kwargs) -> None:
            return None

    file_path = tmp_path / "release.zip"
    file_path.write_bytes(b"zip-content")
    suffix_card = {
        "identity": "release(14).zip Document",
        "title": "release(14).zip",
        "text": "release(14).zip Document",
    }

    async def fake_inspect(*_args, **_kwargs):
        return {
            "ok": True,
            "status": "indexed_source_library_family_inspected",
            "records": [{
                "filename": "release(14).zip",
                "file_size_bytes": file_path.stat().st_size,
                "processed_file_id": "file_000000001234567890abcdef12345678",
                "library_metadata_object_id": "libfile_1234567890abcdef1234567890abcdef",
                "file_id": "file_000000001234567890abcdef12345678",
                "deleted": False,
            }],
        }

    browser_client._inspect_active_library_family_for_source_correlation = fake_inspect  # type: ignore[method-assign]

    result = asyncio.run(browser_client._correlate_existing_indexed_project_source(
        context=Context(),
        page=object(),
        project_url="https://chatgpt.com/g/g-p-123/project",
        canonical_name="release.zip",
        file_path=str(file_path),
        suffix_sources=[suffix_card],
        exact_canonical_sources=[],
    ))

    assert result["ok"] is True
    assert result["status"] == "existing_correlated_source"
    assert result["requested_filename"] == "release.zip"
    assert result["assigned_filename"] == "release(14).zip"
    assert result["processed_file_id"] == "file_000000001234567890abcdef12345678"
    assert result["library_metadata_object_id"] == "libfile_1234567890abcdef1234567890abcdef"
    assert result["content_identity_mode"] == "size_and_uploaded_file_identity"
    assert result["local_sha256"] == hashlib.sha256(file_path.read_bytes()).hexdigest()


def test_processing_stream_terminal_result_requires_exact_completed_identity(browser_client: ChatGPTBrowserClient) -> None:
    body = "\n".join([
        '{"file_id":"file_00000000111122223333444455556666","event":"file.processing.started","message":"start","extra":null}',
        '{"file_id":"file_00000000111122223333444455556666","event":"file.indexing.completed","message":"","extra":{"metadata_object_id":"libfile_abcdef1234567890abcdef1234567890","library_file_name":"release.zip"}}',
        '{"file_id":"file_00000000111122223333444455556666","event":"file.processing.completed","message":"done","extra":null}',
    ])

    result = browser_client._project_source_processing_stream_terminal_result(
        body,
        expected_filename="release.zip",
    )

    assert result is not None
    assert result["status"] == "completed"
    assert result["identity_verified"] is True
    assert result["processed_file_id"] == "file_00000000111122223333444455556666"
    assert result["library_metadata_object_id"] == "libfile_abcdef1234567890abcdef1234567890"
    assert result["library_file_name"] == "release.zip"
    assert result["assigned_filename"] == "release.zip"
    assert result["filename_correlation"] == "exact_canonical"


def test_processing_stream_terminal_result_accepts_indexed_assigned_filename(browser_client: ChatGPTBrowserClient) -> None:
    body = "\n".join([
        '{"file_id":"file_00000000111122223333444455556666","event":"file.processing.started","message":"start","extra":null}',
        '{"file_id":"file_00000000111122223333444455556666","event":"file.indexing.completed","message":"","extra":{"metadata_object_id":"libfile_abcdef1234567890abcdef1234567890","library_file_name":"release(14).zip"}}',
        '{"file_id":"file_00000000111122223333444455556666","event":"file.processing.completed","message":"done","extra":null}',
    ])

    result = browser_client._project_source_processing_stream_terminal_result(body, expected_filename="release.zip")

    assert result is not None
    assert result["identity_verified"] is True
    assert result["requested_filename"] == "release.zip"
    assert result["assigned_filename"] == "release(14).zip"
    assert result["filename_correlation"] == "backend_assigned_indexed"
    assert result["processed_file_id"].startswith("file_")
    assert result["library_metadata_object_id"].startswith("libfile_")


def test_processing_stream_aware_quiet_settle_recovers_when_stream_completes_at_logical_95_seconds(
    browser_client: ChatGPTBrowserClient,
) -> None:
    class LogicalPage:
        def __init__(self, watch: dict) -> None:
            self.watch = watch
            self.logical_elapsed_ms = 0

        async def wait_for_timeout(self, milliseconds: int) -> None:
            self.logical_elapsed_ms += int(milliseconds)
            if self.logical_elapsed_ms >= 95_000 and self.watch.get("processing_stream_terminal") is None:
                self.watch["processing_stream_terminal"] = {
                    "status": "completed",
                    "terminal_event": "file.processing.completed",
                    "terminal_message": "done",
                    "processed_file_id": "file_00000000111122223333444455556666",
                    "library_metadata_object_id": "libfile_abcdef1234567890abcdef1234567890",
                    "library_file_name": "release.zip",
                    "expected_filename": "release.zip",
                    "events": [
                        "file.processing.started",
                        "file.indexing.completed",
                        "file.processing.completed",
                    ],
                    "identity_verified": True,
                }

    async def run() -> tuple[dict, dict, int]:
        loop = asyncio.get_running_loop()
        watch = {
            "source_kind": "file",
            "expected_filename": "release.zip",
            "installed": True,
            "started": 2,
            "finished": 1,
            "failed": 0,
            "saw_relevant": True,
            "saw_commit": True,
            "inflight": {2},
            "processing_stream_inflight": {2},
            "processing_stream_started": 1,
            "processing_stream_finished": 0,
            "processing_stream_failed": 0,
            "processing_stream_terminal": None,
            "last_activity": loop.time() - 5,
            "commit_seen_at": loop.time() - 5,
            "ordinary_response_tasks": [],
            "response_tasks": [],
        }
        page = LogicalPage(watch)
        quiet = await browser_client._wait_for_project_source_save_request_quiet(
            page,
            watch,
            source_kind="file",
            timeout_ms=60_000,
            observation_window_ms=8_000,
            quiet_window_ms=2_000,
        )
        stream = await browser_client._wait_for_project_source_processing_stream(
            page,
            watch,
            source_kind="file",
            expected_filename="release.zip",
            timeout_ms=120_000,
            poll_interval_ms=5_000,
        )
        return quiet, stream, page.logical_elapsed_ms

    quiet, stream, logical_elapsed_ms = asyncio.run(run())

    assert quiet["quiet_now"] is True
    assert quiet["ordinary_inflight"] == 0
    assert quiet["processing_stream_inflight"] == 1
    assert quiet["quiet_reason"] == "ordinary_save_quiet_processing_stream_pending"
    assert stream["status"] == "project_source_processing_stream_completed"
    assert stream["library_metadata_object_id"] == "libfile_abcdef1234567890abcdef1234567890"
    assert logical_elapsed_ms == 95_000


def test_processing_stream_wait_fails_when_terminal_identity_is_incomplete(browser_client: ChatGPTBrowserClient) -> None:
    watch = {
        "processing_stream_started": 1,
        "processing_stream_failed": 0,
        "processing_stream_terminal": {
            "status": "completed",
            "terminal_event": "file.processing.completed",
            "processed_file_id": "file_00000000111122223333444455556666",
            "library_metadata_object_id": None,
            "library_file_name": "release.zip",
            "identity_verified": False,
        },
    }

    class Page:
        async def wait_for_timeout(self, _milliseconds: int) -> None:
            return None

    with pytest.raises(ResponseTimeoutError, match="project_source_processing_stream_identity_not_verified"):
        asyncio.run(
            browser_client._wait_for_project_source_processing_stream(
                Page(),
                watch,
                source_kind="file",
                expected_filename="release.zip",
                timeout_ms=100,
            )
        )


def test_library_backend_diagnostic_exception_reason_is_explicit(browser_client: ChatGPTBrowserClient) -> None:
    assert browser_client._library_backend_protocol_reupload_exception_reason(
        ResponseTimeoutError("fetch_xhr_protocol_watch_settle_timeout: pending_task_count=1")
    ) == "fetch_xhr_protocol_watch_settle_timeout"
    assert browser_client._library_backend_protocol_reupload_exception_reason(
        ResponseTimeoutError("project_source_processing_stream_timeout: release.zip")
    ) == "project_source_processing_stream_timeout"
    assert browser_client._library_backend_protocol_reupload_exception_reason(
        ResponseTimeoutError("Timed out waiting for project source save requests to go quiet")
    ) == "project_source_save_quiet_timeout"
    assert browser_client._library_backend_protocol_reupload_exception_reason(
        ResponseTimeoutError("other timeout")
    ) == "diagnostic_response_timeout"


def test_processing_stream_response_body_is_captured_only_after_requestfinished(
    browser_client: ChatGPTBrowserClient,
) -> None:
    context = _LibraryWatchContext()

    class Request:
        url = "https://chatgpt.com/backend-api/files/process_upload_stream"
        method = "POST"

    request = Request()

    class Response:
        status = 200

        def __init__(self, bound_request) -> None:
            self.request = bound_request
            self.url = bound_request.url

        async def text(self) -> str:
            return "\n".join([
                '{"file_id":"file_00000000111122223333444455556666","event":"file.processing.started","message":"start","extra":null}',
                '{"file_id":"file_00000000111122223333444455556666","event":"file.indexing.completed","message":"","extra":{"metadata_object_id":"libfile_abcdef1234567890abcdef1234567890","library_file_name":"release.zip"}}',
                '{"file_id":"file_00000000111122223333444455556666","event":"file.processing.completed","message":"done","extra":null}',
            ])

        async def all_headers(self):
            return {"content-type": "text/event-stream"}

    async def run() -> dict:
        watch = browser_client._install_project_source_save_request_watch(
            context,
            source_kind="file",
            expected_filename="release.zip",
        )
        context.handlers["request"](request)
        context.handlers["response"](Response(request))
        await asyncio.sleep(0)
        assert watch["processing_stream_terminal"] is None
        assert watch["processing_stream_response_tasks"] == []
        assert id(request) in watch["processing_stream_responses"]

        context.handlers["requestfinished"](request)
        await asyncio.gather(*watch["processing_stream_response_tasks"])
        return watch

    watch = asyncio.run(run())
    terminal = watch["processing_stream_terminal"]
    assert terminal["status"] == "completed"
    assert terminal["identity_verified"] is True
    assert terminal["processed_file_id"] == "file_00000000111122223333444455556666"
    assert terminal["library_metadata_object_id"] == "libfile_abcdef1234567890abcdef1234567890"
    assert terminal["library_file_name"] == "release.zip"


def test_file_add_orders_processing_before_persistence_and_disposal(
    browser_client: ChatGPTBrowserClient,
    tmp_path: Path,
) -> None:
    page = object()
    order: list[str] = []
    persisted = {
        "identity": "release.zip",
        "title": "release.zip",
        "text": "release.zip",
        "_promptbranch_verification_mode": "post_refresh",
    }

    async def fake_noop(*_args, **_kwargs):
        return None

    async def fake_find_existing(*_args, **_kwargs):
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return []

    async def fake_presence(*_args, **_kwargs):
        return dict(persisted)

    async def fake_quiet(*_args, **_kwargs):
        order.append("ordinary_quiet")
        return {
            "quiet_now": True,
            "saw_commit": False,
            "started": 2,
            "finished": 1,
            "failed": 0,
            "ordinary_inflight": 0,
            "processing_stream_inflight": 1,
        }

    async def fake_processing(*_args, **_kwargs):
        order.append("processing_completion")
        return {
            "ok": True,
            "status": "project_source_processing_stream_completed",
            "processed_file_id": "file_00000000111122223333444455556666",
            "library_metadata_object_id": "libfile_abcdef1234567890abcdef1234567890",
            "library_file_name": "release.zip",
        }

    async def fake_persistence(*_args, **_kwargs):
        order.append("persistence_verification")
        return dict(persisted)

    async def fake_safe_url(*_args, **_kwargs):
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    watch = {
        "installed": True,
        "source_kind": "file",
        "expected_filename": "release.zip",
        "started": 2,
        "finished": 1,
        "failed": 0,
        "saw_relevant": True,
        "saw_commit": False,
        "inflight": {2},
        "processing_stream_inflight": {2},
        "processing_stream_started": 1,
        "processing_stream_finished": 0,
        "processing_stream_failed": 0,
        "processing_stream_terminal": None,
        "responses": [],
        "backend_assigned_names": ["release.zip"],
        "backing_file_ids": ["file_00000000111122223333444455556666"],
    }

    browser_client.ensure_logged_in = fake_noop  # type: ignore[method-assign]
    browser_client._goto = fake_noop  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_noop  # type: ignore[method-assign]
    browser_client._find_existing_file_source_for_overwrite = fake_find_existing  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._add_project_file_source = fake_noop  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fake_presence  # type: ignore[method-assign]
    browser_client._wait_for_project_source_post_save_settle = fake_noop  # type: ignore[method-assign]
    browser_client._wait_for_project_source_save_request_quiet = fake_quiet  # type: ignore[method-assign]
    browser_client._wait_for_project_source_processing_stream = fake_processing  # type: ignore[method-assign]
    browser_client._verify_project_source_persistence = fake_persistence  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_url  # type: ignore[method-assign]
    browser_client._install_project_source_save_request_watch = lambda *_args, **_kwargs: watch  # type: ignore[method-assign]

    def fake_dispose(*_args, **_kwargs) -> None:
        order.append("watcher_disposal")

    browser_client._dispose_project_source_save_request_watch = fake_dispose  # type: ignore[method-assign]

    file_path = tmp_path / "release.zip"
    file_path.write_bytes(b"zip")
    result = asyncio.run(
        browser_client._add_project_source_operation(
            context=None,
            page=page,
            source_kind="file",
            value=None,
            file_path=str(file_path),
            display_name=str(file_path),
            keep_open=False,
        )
    )

    assert result["ok"] is True
    assert result["processing_stream"]["status"] == "project_source_processing_stream_completed"
    assert order == [
        "ordinary_quiet",
        "processing_completion",
        "persistence_verification",
        "watcher_disposal",
    ]


def test_file_add_reports_post_processing_persistence_failure_explicitly(
    browser_client: ChatGPTBrowserClient,
    tmp_path: Path,
) -> None:
    page = object()
    disposed: list[bool] = []
    persisted = {"identity": "release.zip", "title": "release.zip", "text": "release.zip"}

    async def fake_noop(*_args, **_kwargs):
        return None

    async def fake_find_existing(*_args, **_kwargs):
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return []

    async def fake_presence(*_args, **_kwargs):
        return dict(persisted)

    async def fake_quiet(*_args, **_kwargs):
        return {"quiet_now": True, "saw_commit": False, "started": 2, "finished": 1, "failed": 0}

    async def fake_processing(*_args, **_kwargs):
        return {
            "ok": True,
            "status": "project_source_processing_stream_completed",
            "processed_file_id": "file_00000000111122223333444455556666",
            "library_metadata_object_id": "libfile_abcdef1234567890abcdef1234567890",
            "library_file_name": "release.zip",
        }

    async def fake_persistence(*_args, **_kwargs):
        raise ResponseTimeoutError("source card absent after completed processing")

    async def fake_safe_url(*_args, **_kwargs):
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    watch = {
        "installed": True,
        "source_kind": "file",
        "expected_filename": "release.zip",
        "started": 2,
        "finished": 2,
        "failed": 0,
        "saw_relevant": True,
        "saw_commit": False,
        "inflight": set(),
        "processing_stream_inflight": set(),
        "processing_stream_started": 1,
        "processing_stream_finished": 1,
        "processing_stream_failed": 0,
        "responses": [],
        "backend_assigned_names": ["release.zip"],
        "backing_file_ids": ["file_00000000111122223333444455556666"],
    }

    browser_client.ensure_logged_in = fake_noop  # type: ignore[method-assign]
    browser_client._goto = fake_noop  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_noop  # type: ignore[method-assign]
    browser_client._find_existing_file_source_for_overwrite = fake_find_existing  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._add_project_file_source = fake_noop  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fake_presence  # type: ignore[method-assign]
    browser_client._wait_for_project_source_post_save_settle = fake_noop  # type: ignore[method-assign]
    browser_client._wait_for_project_source_save_request_quiet = fake_quiet  # type: ignore[method-assign]
    browser_client._wait_for_project_source_processing_stream = fake_processing  # type: ignore[method-assign]
    browser_client._verify_project_source_persistence = fake_persistence  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_url  # type: ignore[method-assign]
    browser_client._install_project_source_save_request_watch = lambda *_args, **_kwargs: watch  # type: ignore[method-assign]
    browser_client._dispose_project_source_save_request_watch = lambda *_args, **_kwargs: disposed.append(True)  # type: ignore[method-assign]

    file_path = tmp_path / "release.zip"
    file_path.write_bytes(b"zip")
    result = asyncio.run(
        browser_client._add_project_source_operation(
            context=None,
            page=page,
            source_kind="file",
            value=None,
            file_path=str(file_path),
            display_name=str(file_path),
            keep_open=False,
        )
    )

    assert result["ok"] is False
    assert result["status"] == "project_source_persistence_not_verified_after_processing_completion"
    assert result["processing_stream"]["status"] == "project_source_processing_stream_completed"
    assert disposed == [True]


def test_file_add_disposes_watcher_when_processing_stream_fails_before_persistence(
    browser_client: ChatGPTBrowserClient,
    tmp_path: Path,
) -> None:
    page = object()
    calls: list[str] = []

    async def fake_noop(*_args, **_kwargs):
        return None

    async def fake_find_existing(*_args, **_kwargs):
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return []

    async def fake_presence(*_args, **_kwargs):
        return {"identity": "release.zip", "title": "release.zip", "text": "release.zip"}

    async def fake_quiet(*_args, **_kwargs):
        calls.append("quiet")
        return {"quiet_now": True, "saw_commit": False, "started": 2, "finished": 1, "failed": 0}

    async def fake_processing(*_args, **_kwargs):
        calls.append("processing")
        raise ResponseTimeoutError("project_source_processing_stream_failed: event=file.processing.failed")

    async def fake_persistence(*_args, **_kwargs):
        calls.append("persistence")
        raise AssertionError("persistence must not run after processing failure")

    async def fake_no_duplicate(*_args, **_kwargs):
        return None

    watch = {"installed": True, "source_kind": "file", "started": 2, "finished": 1, "failed": 0}
    browser_client.ensure_logged_in = fake_noop  # type: ignore[method-assign]
    browser_client._goto = fake_noop  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_noop  # type: ignore[method-assign]
    browser_client._find_existing_file_source_for_overwrite = fake_find_existing  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._add_project_file_source = fake_noop  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fake_presence  # type: ignore[method-assign]
    browser_client._wait_for_project_source_post_save_settle = fake_noop  # type: ignore[method-assign]
    browser_client._wait_for_project_source_save_request_quiet = fake_quiet  # type: ignore[method-assign]
    browser_client._wait_for_project_source_processing_stream = fake_processing  # type: ignore[method-assign]
    browser_client._verify_project_source_persistence = fake_persistence  # type: ignore[method-assign]
    browser_client._find_project_source_duplicate_notice = fake_no_duplicate  # type: ignore[method-assign]
    browser_client._install_project_source_save_request_watch = lambda *_args, **_kwargs: watch  # type: ignore[method-assign]
    browser_client._dispose_project_source_save_request_watch = lambda *_args, **_kwargs: calls.append("dispose")  # type: ignore[method-assign]

    file_path = tmp_path / "release.zip"
    file_path.write_bytes(b"zip")
    with pytest.raises(ResponseTimeoutError, match="project_source_processing_stream_failed"):
        asyncio.run(
            browser_client._add_project_source_operation(
                context=None,
                page=page,
                source_kind="file",
                value=None,
                file_path=str(file_path),
                display_name=str(file_path),
                keep_open=False,
            )
        )

    assert calls == ["quiet", "processing", "dispose"]


def test_legacy_diagnostic_file_add_orders_processing_before_persistence_and_disposal(
    browser_client: ChatGPTBrowserClient,
    tmp_path: Path,
) -> None:
    page = object()
    order: list[str] = []
    persisted = {
        "identity": "diagnostic.txt",
        "title": "diagnostic.txt",
        "text": "diagnostic.txt",
        "_promptbranch_verification_mode": "post_refresh",
    }

    async def fake_noop(*_args, **_kwargs):
        return None

    async def fake_find_existing(*_args, **_kwargs):
        return None

    async def fake_snapshot(*_args, **_kwargs):
        return []

    async def fake_presence(*_args, **_kwargs):
        return dict(persisted)

    async def fake_quiet(*_args, **_kwargs):
        order.append("ordinary_quiet")
        return {
            "quiet_now": True,
            "quiet_reason": "ordinary_save_quiet_processing_stream_pending",
            "processing_stream_pending": True,
            "saw_commit": True,
            "started": 2,
            "finished": 1,
            "failed": 0,
            "ordinary_inflight": 0,
            "processing_stream_inflight": 1,
        }

    async def fake_processing(*_args, **_kwargs):
        order.append("processing_completion")
        return {
            "ok": True,
            "status": "project_source_processing_stream_completed",
            "processed_file_id": "file_00000000111122223333444455556666",
            "library_metadata_object_id": "libfile_abcdef1234567890abcdef1234567890",
            "library_file_name": "diagnostic.txt",
            "terminal_event": "file.processing.completed",
        }

    async def fake_persistence(*_args, **_kwargs):
        order.append("persistence_verification")
        return dict(persisted)

    async def fake_safe_url(*_args, **_kwargs):
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    watch = {
        "installed": True,
        "source_kind": "file",
        "expected_filename": "diagnostic.txt",
        "started": 2,
        "finished": 2,
        "failed": 0,
        "saw_relevant": True,
        "saw_commit": True,
        "inflight": set(),
        "processing_stream_inflight": set(),
        "processing_stream_started": 1,
        "processing_stream_finished": 1,
        "processing_stream_failed": 0,
        "processing_stream_terminal": {
            "status": "completed",
            "identity_verified": True,
        },
        "responses": [],
        "backend_assigned_names": ["diagnostic.txt"],
        "backing_file_ids": ["file_00000000111122223333444455556666"],
    }

    browser_client.ensure_logged_in = fake_noop  # type: ignore[method-assign]
    browser_client._goto = fake_noop  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_noop  # type: ignore[method-assign]
    browser_client._find_existing_file_source_for_overwrite = fake_find_existing  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._add_project_file_source = fake_noop  # type: ignore[method-assign]
    browser_client._wait_for_source_presence = fake_presence  # type: ignore[method-assign]
    browser_client._wait_for_project_source_post_save_settle = fake_noop  # type: ignore[method-assign]
    browser_client._wait_for_project_source_save_request_quiet = fake_quiet  # type: ignore[method-assign]
    browser_client._wait_for_project_source_processing_stream = fake_processing  # type: ignore[method-assign]
    browser_client._verify_project_source_persistence = fake_persistence  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_url  # type: ignore[method-assign]
    browser_client._install_project_source_save_request_watch = lambda *_args, **_kwargs: watch  # type: ignore[method-assign]

    def fake_dispose(*_args, **_kwargs) -> None:
        order.append("watcher_disposal")

    browser_client._dispose_project_source_save_request_watch = fake_dispose  # type: ignore[method-assign]

    file_path = tmp_path / "diagnostic.txt"
    file_path.write_text("diagnostic", encoding="utf-8")
    result = asyncio.run(
        browser_client._add_project_source_operation_legacy_10_75(
            context=None,
            page=page,
            source_kind="file",
            value=None,
            file_path=str(file_path),
            display_name=str(file_path),
            keep_open=False,
            overwrite_existing=False,
        )
    )

    assert result["ok"] is True
    assert result["processing_stream"]["status"] == "project_source_processing_stream_completed"
    assert order == [
        "ordinary_quiet",
        "processing_completion",
        "persistence_verification",
        "watcher_disposal",
    ]


def test_processing_stream_pending_without_result_is_internal_contract_failure(
    browser_client: ChatGPTBrowserClient,
) -> None:
    invariant = browser_client._project_source_processing_stream_result_invariant(
        {
            "save_request_quiet": {
                "processing_stream_pending": True,
                "quiet_reason": "ordinary_save_quiet_processing_stream_pending",
            },
            "processing_stream": None,
        }
    )
    assert invariant == {
        "ok": False,
        "status": "internal_processing_stream_wait_skipped",
        "processing_stream_pending": True,
        "processing_stream_result_present": False,
        "processing_stream_status": None,
        "quiet_reason": "ordinary_save_quiet_processing_stream_pending",
    }


def test_add_file_source_replaces_previous_indexed_family_member_after_new_assignment(
    browser_client: ChatGPTBrowserClient,
    tmp_path: Path,
) -> None:
    class Context:
        def on(self, *_args, **_kwargs) -> None:
            return None

    page = object()
    older_card = {
        "identity": "release(15).zip File contents may not be accessible",
        "title": "release(15).zip",
        "text": "release(15).zip File contents may not be accessible",
    }
    old_card = {
        "identity": "release(16).zip File contents may not be accessible",
        "title": "release(16).zip",
        "text": "release(16).zip File contents may not be accessible",
    }
    new_card = {
        "identity": "release(17).zip File contents may not be accessible",
        "title": "release(17).zip",
        "text": "release(17).zip File contents may not be accessible",
    }
    visible_sources = [older_card, old_card, new_card]
    calls = {"uploads": 0, "removes": [], "generic_verify": 0}
    processed_file_id = "file_000000001234567890abcdef12345678"
    library_object_id = "libfile_1234567890abcdef1234567890abcdef"

    async def fake_noop(*_args, **_kwargs) -> None:
        return None

    authority_calls = 0

    async def fake_authority(*_args, **_kwargs):
        nonlocal authority_calls
        authority_calls += 1
        sources = [older_card, old_card] if authority_calls == 1 else list(visible_sources)
        return {
            "ok": True,
            "status": "authoritative",
            "sources": sources,
            "source_card_count": len(sources),
            "source_identities": [item["identity"] for item in sources],
            "empty_state_visible": False,
        }

    async def fake_upload(*_args, **_kwargs) -> None:
        calls["uploads"] += 1

    async def fake_settle(*_args, **_kwargs):
        return {"settled": True}

    async def fake_quiet(*_args, **_kwargs):
        return {"saw_commit": True, "started": 2, "finished": 2, "failed": 0, "inflight": 0}

    async def fake_processing(*_args, **_kwargs):
        return {
            "status": "project_source_processing_stream_completed",
            "assigned_filename": "release(17).zip",
            "library_file_name": "release(17).zip",
            "processed_file_id": processed_file_id,
            "library_metadata_object_id": library_object_id,
        }

    async def fake_snapshot(*_args, **_kwargs):
        return list(visible_sources)

    async def fake_remove(*_args, **kwargs):
        target = kwargs["source_name"]
        calls["removes"].append(target)
        assert kwargs["exact"] is True
        visible_sources[:] = [item for item in visible_sources if item["title"] != target]
        return {
            "ok": True,
            "action": "remove",
            "source_name": target,
            "source_match": target,
            "source_identity_used": target,
            "exact": True,
            "removed_via_ui": True,
            "already_absent": False,
        }

    async def fail_generic_verify(*_args, **_kwargs):
        calls["generic_verify"] += 1
        raise AssertionError("assigned-name fast verification must skip canonical persistence retries")

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client.ensure_logged_in = fake_noop  # type: ignore[method-assign]
    browser_client._goto = fake_noop  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_noop  # type: ignore[method-assign]
    browser_client._wait_for_authoritative_project_sources_surface = fake_authority  # type: ignore[method-assign]
    browser_client._add_project_file_source = fake_upload  # type: ignore[method-assign]
    browser_client._wait_for_project_source_post_save_settle = fake_settle  # type: ignore[method-assign]
    browser_client._wait_for_project_source_save_request_quiet = fake_quiet  # type: ignore[method-assign]
    browser_client._wait_for_project_source_processing_stream = fake_processing  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._remove_project_source_operation = fake_remove  # type: ignore[method-assign]
    browser_client._verify_project_source_persistence = fail_generic_verify  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._install_project_source_save_request_watch = lambda *_args, **_kwargs: {
        "installed": True,
        "source_kind": "file",
        "started": 2,
        "finished": 2,
        "failed": 0,
        "saw_relevant": True,
        "saw_commit": True,
        "inflight": set(),
        "backing_file_ids": [processed_file_id],
        "backend_assigned_names": ["release.zip", "release(17).zip"],
    }  # type: ignore[method-assign]
    browser_client._dispose_project_source_save_request_watch = lambda *_args, **_kwargs: None  # type: ignore[method-assign]

    file_path = tmp_path / "release.zip"
    file_path.write_bytes(b"zip")
    result = asyncio.run(
        browser_client._add_project_source_operation(
            context=Context(),
            page=page,
            source_kind="file",
            value=None,
            file_path=str(file_path),
            display_name=str(file_path),
            keep_open=False,
        )
    )

    assert calls == {"uploads": 1, "removes": ["release(15).zip", "release(16).zip"], "generic_verify": 0}
    assert result["ok"] is True
    assert result["status"] == "source_replaced"
    assert result["requested_filename"] == "release.zip"
    assert result["assigned_filename"] == "release(17).zip"
    assert result["previous_max_assigned_index"] == 16
    assert result["assigned_index"] == 17
    assert result["family_replacement_required"] is True
    assert result["family_replacement_performed"] is True
    assert result["family_replacement_verified"] is True
    assert result["removed_family_source_count"] == 2
    assert result["final_family_source_count"] == 1
    assert result["final_family_source_identities"] == [new_card["identity"]]
    assert result["duplicate_suffix_source_count"] == 1
    assert result["duplicate_suffix_source_identities"] == [new_card["identity"]]
    assert result["removed_existing"] is True
    assert result["overwritten"] is True


def test_add_file_source_blocks_success_when_previous_family_member_removal_fails(
    browser_client: ChatGPTBrowserClient,
    tmp_path: Path,
) -> None:
    class Context:
        def on(self, *_args, **_kwargs) -> None:
            return None

    page = object()
    old_card = {"identity": "release(16).zip Document", "title": "release(16).zip", "text": "release(16).zip Document"}
    new_card = {"identity": "release(17).zip Document", "title": "release(17).zip", "text": "release(17).zip Document"}
    processed_file_id = "file_000000001234567890abcdef12345678"
    library_object_id = "libfile_1234567890abcdef1234567890abcdef"

    async def fake_noop(*_args, **_kwargs) -> None:
        return None

    async def fake_preflight(*_args, **_kwargs):
        return {"ok": True, "status": "authoritative", "sources": [old_card], "source_card_count": 1, "source_identities": [old_card["identity"]], "empty_state_visible": False}

    async def fake_upload(*_args, **_kwargs) -> None:
        return None

    async def fake_settle(*_args, **_kwargs):
        return {"settled": True}

    async def fake_quiet(*_args, **_kwargs):
        return {"saw_commit": True, "started": 2, "finished": 2, "failed": 0, "inflight": 0}

    async def fake_processing(*_args, **_kwargs):
        return {"status": "project_source_processing_stream_completed", "assigned_filename": "release(17).zip", "library_file_name": "release(17).zip", "processed_file_id": processed_file_id, "library_metadata_object_id": library_object_id}

    async def fake_snapshot(*_args, **_kwargs):
        return [old_card, new_card]

    async def fake_remove(*_args, **_kwargs):
        raise ResponseTimeoutError("old source did not disappear")

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client.ensure_logged_in = fake_noop  # type: ignore[method-assign]
    browser_client._goto = fake_noop  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_noop  # type: ignore[method-assign]
    browser_client._wait_for_authoritative_project_sources_surface = fake_preflight  # type: ignore[method-assign]
    browser_client._add_project_file_source = fake_upload  # type: ignore[method-assign]
    browser_client._wait_for_project_source_post_save_settle = fake_settle  # type: ignore[method-assign]
    browser_client._wait_for_project_source_save_request_quiet = fake_quiet  # type: ignore[method-assign]
    browser_client._wait_for_project_source_processing_stream = fake_processing  # type: ignore[method-assign]
    browser_client._snapshot_project_source_cards = fake_snapshot  # type: ignore[method-assign]
    browser_client._remove_project_source_operation = fake_remove  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    browser_client._install_project_source_save_request_watch = lambda *_args, **_kwargs: {
        "installed": True,
        "source_kind": "file",
        "started": 2,
        "finished": 2,
        "failed": 0,
        "saw_relevant": True,
        "saw_commit": True,
        "inflight": set(),
        "backing_file_ids": [processed_file_id],
        "backend_assigned_names": ["release(17).zip"],
    }  # type: ignore[method-assign]
    browser_client._dispose_project_source_save_request_watch = lambda *_args, **_kwargs: None  # type: ignore[method-assign]

    file_path = tmp_path / "release.zip"
    file_path.write_bytes(b"zip")
    result = asyncio.run(browser_client._add_project_source_operation(context=Context(), page=page, source_kind="file", value=None, file_path=str(file_path), display_name=str(file_path), keep_open=False))

    assert result["ok"] is False
    assert result["status"] == "source_family_previous_member_remove_failed"
    assert result["persistence_verified"] is True
    assert result["project_source_mutated"] is True
    assert result["release_blocking"] is True
    assert result["operator_review_required"] is True
    assert result["family_replacement_required"] is True
    assert result["family_replacement_verified"] is False
    assert result["assigned_filename"] == "release(17).zip"


def test_add_file_source_no_overwrite_blocks_existing_indexed_family_before_upload(
    browser_client: ChatGPTBrowserClient,
    tmp_path: Path,
) -> None:
    page = object()
    old_card = {"identity": "release(16).zip Document", "title": "release(16).zip", "text": "release(16).zip Document"}
    calls = {"uploads": 0}

    async def fake_noop(*_args, **_kwargs) -> None:
        return None

    async def fake_preflight(*_args, **_kwargs):
        return {"ok": True, "status": "authoritative", "sources": [old_card], "source_card_count": 1, "source_identities": [old_card["identity"]], "empty_state_visible": False}

    async def forbidden_upload(*_args, **_kwargs) -> None:
        calls["uploads"] += 1

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    browser_client.ensure_logged_in = fake_noop  # type: ignore[method-assign]
    browser_client._goto = fake_noop  # type: ignore[method-assign]
    browser_client._open_project_sources_tab = fake_noop  # type: ignore[method-assign]
    browser_client._wait_for_authoritative_project_sources_surface = fake_preflight  # type: ignore[method-assign]
    browser_client._add_project_file_source = forbidden_upload  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]

    file_path = tmp_path / "release.zip"
    file_path.write_bytes(b"zip")
    result = asyncio.run(
        browser_client._add_project_source_operation(
            context=None,
            page=page,
            source_kind="file",
            value=None,
            file_path=str(file_path),
            display_name=str(file_path),
            keep_open=False,
            overwrite_existing=False,
        )
    )

    assert calls["uploads"] == 0
    assert result["ok"] is False
    assert result["status"] == "source_family_exists_no_overwrite"
    assert result["project_source_mutated"] is False
    assert result["pre_upload_family_source_count"] == 1
    assert result["previous_max_assigned_index"] == 16
