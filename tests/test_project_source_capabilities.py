from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from chatgpt_browser_auth.client import ChatGPTBrowserClient
from chatgpt_browser_auth.config import ChatGPTBrowserConfig
from chatgpt_browser_auth.exceptions import UnsupportedOperationError


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


def test_verify_project_source_persistence_refreshes_sources_url(browser_client: ChatGPTBrowserClient) -> None:
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

    assert persisted == {"identity": "pasted.txt Document"}
    assert calls[0] == (
        "goto",
        page,
        "https://chatgpt.com/g/g-p-123/project?tab=sources",
        "project-source-add-persistence-refresh",
    )
    assert calls[1][0] == "wait"
    assert calls[1][1] is page
    assert calls[1][2]["source_match_candidates"] == ["pasted.txt Document"]
    assert calls[1][2]["before_sources"] is None
    assert calls[1][2]["accept_single_new_card"] is False


def test_add_project_source_operation_requires_post_refresh_persistence(browser_client: ChatGPTBrowserClient) -> None:
    page = object()

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
        return {
            "identity": "pasted.txt Document",
            "title": "pasted.txt",
            "subtitle": "Document",
            "text": "pasted.txt\nDocument",
        }

    async def fake_verify_persistence(*_args, **kwargs):
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
    browser_client._verify_project_source_persistence = fake_verify_persistence  # type: ignore[method-assign]
    browser_client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]

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

    assert result["ok"] is True
    assert result["source_match"] == "pasted.txt Document"
    assert result["source_match_requested"] == "Integration note for run 123"
    assert result["persistence_verified"] is True
