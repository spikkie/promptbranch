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
