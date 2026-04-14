from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from chatgpt_browser_auth.client import ChatGPTBrowserClient
from chatgpt_browser_auth.config import ChatGPTBrowserConfig


@dataclass
class FakePage:
    evaluate_result: object | None = None

    async def evaluate(self, _script: str):
        return self.evaluate_result

    async def wait_for_timeout(self, _ms: int) -> None:
        return None


def _make_client(tmp_path: Path) -> ChatGPTBrowserClient:
    config = ChatGPTBrowserConfig(
        project_url="https://chatgpt.com/",
        profile_dir=str(tmp_path / "profile"),
        debug=False,
        save_trace=False,
        save_html=False,
        save_screenshot=False,
    )
    return ChatGPTBrowserClient(config)


def test_collect_sidebar_projects_uses_anchor_urls_without_extra_validation(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    page = FakePage(
        evaluate_result=[
            {
                "name": "Test_Test_3",
                "url": "https://chatgpt.com/g/g-p-69de540eadf88191b04ad8fd42ec8835-test-test-3/project?foo=bar",
            },
            {
                "name": "test_test_3 duplicate",
                "url": "https://chatgpt.com/g/g-p-69de540eadf88191b04ad8fd42ec8835-test-test-3/project",
            },
            {
                "name": "Ignored",
                "url": "https://chatgpt.com/not-a-project",
            },
        ]
    )

    result = asyncio.run(client._collect_sidebar_projects(page))

    assert result == [
        {
            "name": "Test_Test_3",
            "url": "https://chatgpt.com/g/g-p-69de540eadf88191b04ad8fd42ec8835-test-test-3/project",
        }
    ]


def test_resolve_project_retries_anchor_enumeration_before_not_found(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    page = FakePage()

    discovered = iter(
        [
            [],
            [],
            [
                {
                    "name": "Test_Test_3",
                    "url": "https://chatgpt.com/g/g-p-69de540eadf88191b04ad8fd42ec8835-test-test-3/project",
                }
            ],
        ]
    )

    async def fake_goto(*_args, **_kwargs) -> None:
        return None

    async def fake_ensure_sidebar_open(*_args, **_kwargs) -> None:
        return None

    async def fake_expand_projects_section(*_args, **_kwargs) -> bool:
        return True

    async def fake_prime_project_sidebar(*_args, **_kwargs) -> None:
        return None

    async def fake_collect_sidebar_projects(*_args, **_kwargs):
        return next(discovered)

    client._goto = fake_goto  # type: ignore[method-assign]
    client._ensure_sidebar_open = fake_ensure_sidebar_open  # type: ignore[method-assign]
    client._expand_projects_section = fake_expand_projects_section  # type: ignore[method-assign]
    client._prime_project_sidebar = fake_prime_project_sidebar  # type: ignore[method-assign]
    client._collect_sidebar_projects = fake_collect_sidebar_projects  # type: ignore[method-assign]

    result = asyncio.run(client._resolve_projects_by_name(page, name="test_test_3", label="project-resolve-home"))

    assert result["error"] is None
    assert result["match_count"] == 1
    assert result["matched_by"] == "exact_name"
    assert result["project_url"] == "https://chatgpt.com/g/g-p-69de540eadf88191b04ad8fd42ec8835-test-test-3/project"


def test_project_url_identity_uses_project_id_for_slugged_and_unslugged_urls(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    short_url = "https://chatgpt.com/g/g-p-69de540eadf88191b04ad8fd42ec8835/project"
    slugged_url = "https://chatgpt.com/g/g-p-69de540eadf88191b04ad8fd42ec8835-test-test-3/project"

    assert client._extract_project_id_from_url(short_url) == "g-p-69de540eadf88191b04ad8fd42ec8835"
    assert client._extract_project_id_from_url(slugged_url) == "g-p-69de540eadf88191b04ad8fd42ec8835"
    assert client._project_urls_refer_to_same_project(short_url, slugged_url) is True


def test_dedupe_projects_collapses_slugged_and_unslugged_variants_by_project_id(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    projects = [
        {
            "name": "test_test_3",
            "url": "https://chatgpt.com/g/g-p-69de540eadf88191b04ad8fd42ec8835/project",
        },
        {
            "name": "test_test_3",
            "url": "https://chatgpt.com/g/g-p-69de540eadf88191b04ad8fd42ec8835-test-test-3/project",
        },
    ]

    assert client._dedupe_projects(projects) == [
        {
            "name": "test_test_3",
            "url": "https://chatgpt.com/g/g-p-69de540eadf88191b04ad8fd42ec8835/project",
        }
    ]
