from __future__ import annotations

import asyncio
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

    async def fake_goto(target_page, url: str, *, label: str) -> None:
        calls.append(("goto", target_page, url, label))

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

    async def fake_goto(target_page, url: str, *, label: str) -> None:
        calls.append(("goto", target_page, url, label))

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
    )
    assert calls[2][0] == "wait"
    assert calls[2][3] == 2
    assert page.wait_calls == []


def test_build_persistence_source_candidates_adds_text_generic_fallback_when_new(browser_client: ChatGPTBrowserClient) -> None:
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
        "pasted.txt Document",
        "pasted.txt",
    ]


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
            "pasted.txt Document",
            "pasted.txt",
        ]
        return {"identity": "pasted.txt Document", "title": "pasted.txt", "text": "pasted.txt Document"}

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
    assert result["source_match"] == "pasted.txt Document"
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




def test_add_project_source_operation_reduces_absence_preflight_for_nonempty_snapshot_miss(browser_client: ChatGPTBrowserClient, tmp_path: Path) -> None:
    page = object()
    calls: dict[str, object] = {
        "preflight_presence_calls": 0,
        "post_upload_presence_calls": 0,
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

    async def fake_wait_for_source_presence(*_args, **kwargs):
        if not calls["added"]:
            calls["preflight_presence_calls"] = int(calls["preflight_presence_calls"]) + 1
            assert kwargs["timeout_ms"] <= 750
            raise ResponseTimeoutError("reduced absence probe did not find requested source")
        calls["post_upload_presence_calls"] = int(calls["post_upload_presence_calls"]) + 1
        return {
            "identity": "itest-file.txt Document",
            "title": "itest-file.txt Document",
            "text": "itest-file.txt Document · Jun 10, 2026",
        }

    async def fake_remove(*_args, **_kwargs):
        calls["removed"] = True
        raise AssertionError("absence preflight miss must not remove any source")

    async def fake_add_file_source(*_args, **_kwargs) -> None:
        calls["added"] = True

    async def fake_wait_for_post_save_settle(*_args, **_kwargs):
        return None

    async def fake_wait_for_quiet(*_args, **_kwargs):
        return None

    async def fake_verify_persistence(*_args, **_kwargs):
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
    browser_client._wait_for_source_presence = fake_wait_for_source_presence  # type: ignore[method-assign]
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

    assert calls["preflight_presence_calls"] == 1
    assert calls["post_upload_presence_calls"] == 1
    assert calls["removed"] is False
    assert calls["added"] is True
    assert result["ok"] is True
    assert result["already_exists"] is False
    assert result["overwritten"] is False
    assert result["removed_existing"] is False


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
        if snapshot_calls["count"] == 1:
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

    assert call_order == [
        "remove:chatgpt_claudecode_workflow_v0.0.275.zip",
        "add_file",
        "presence",
        "settle",
        "save_quiet",
        "verify",
    ]
    assert result["ok"] is True
    assert result["capacity_pruned"] is True
    assert result["removed_existing"] is True
    assert result["capacity_prune_result"]["source_name"] == "chatgpt_claudecode_workflow_v0.0.275.zip"
