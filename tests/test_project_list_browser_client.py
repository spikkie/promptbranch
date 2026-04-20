from pathlib import Path

from promptbranch_browser_auth.client import ChatGPTBrowserClient
from promptbranch_browser_auth.config import ChatGPTBrowserConfig


def _make_client(tmp_path: Path) -> ChatGPTBrowserClient:
    profile_dir = tmp_path / "profile"
    profile_dir.mkdir()
    config = ChatGPTBrowserConfig(
        email="user@example.com",
        password="secret",
        project_url="https://chatgpt.com/g/g-p-current-demo/project",
        profile_dir=str(profile_dir),
        headless=True,
    )
    return ChatGPTBrowserClient(config)


def test_list_projects_operation_normalizes_sidebar_projects(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class DummyPage:
        async def wait_for_timeout(self, ms):
            return None

    page = DummyPage()

    async def fake_ensure_logged_in(page, context):
        return None

    async def fake_goto(page, url, label=None):
        return None

    async def fake_sidebar(page):
        return None

    async def fake_expand(page):
        return None

    async def fake_prime(page):
        return None

    async def fake_collect(page):
        return [
            {"name": "Alpha", "url": "https://chatgpt.com/g/g-p-alpha-demo/project"},
            {"name": "Current", "url": "https://chatgpt.com/g/g-p-current-demo/project"},
        ]

    async def fake_safe_page_url(page):
        return "https://chatgpt.com/"

    client.ensure_logged_in = fake_ensure_logged_in
    client._goto = fake_goto
    client._ensure_sidebar_open = fake_sidebar
    client._expand_projects_section = fake_expand
    client._prime_project_sidebar = fake_prime
    client._collect_sidebar_projects = fake_collect
    client._safe_page_url = fake_safe_page_url

    import asyncio

    result = asyncio.run(client._list_projects_operation(context=None, page=page, keep_open=False))
    assert result["ok"] is True
    assert result["count"] == 2
    assert result["current_project_url"] == "https://chatgpt.com/g/g-p-current-demo/project"
    assert any(item["is_current"] for item in result["projects"])
    current = next(item for item in result["projects"] if item["is_current"])
    assert current["project_id"] == "g-p-current"
    assert current["project_slug"] == "g-p-current-demo"


def test_collect_all_sidebar_projects_scrolls_until_stable(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class DummyPage:
        def __init__(self) -> None:
            self.waits: list[int] = []

        async def wait_for_timeout(self, ms):
            self.waits.append(ms)
            return None

    page = DummyPage()

    discovered = iter(
        [
            [{"name": "Alpha", "url": "https://chatgpt.com/g/g-p-alpha-demo/project"}],
            [
                {"name": "Alpha", "url": "https://chatgpt.com/g/g-p-alpha-demo/project"},
                {"name": "Beta", "url": "https://chatgpt.com/g/g-p-beta-demo/project"},
            ],
            [
                {"name": "Alpha", "url": "https://chatgpt.com/g/g-p-alpha-demo/project"},
                {"name": "Beta", "url": "https://chatgpt.com/g/g-p-beta-demo/project"},
            ],
            [
                {"name": "Alpha", "url": "https://chatgpt.com/g/g-p-alpha-demo/project"},
                {"name": "Beta", "url": "https://chatgpt.com/g/g-p-beta-demo/project"},
            ],
        ]
    )
    moved = iter([True, False])

    async def fake_collect(_page):
        return next(discovered)

    async def fake_scroll(_page):
        return next(moved)

    client._collect_sidebar_projects = fake_collect
    client._scroll_project_sidebar_step = fake_scroll

    import asyncio

    result = asyncio.run(client._collect_all_sidebar_projects(page, label="project-list", max_scroll_rounds=5))
    assert [item["name"] for item in result] == ["Alpha", "Beta"]
    assert page.waits == [250]


def test_collect_all_sidebar_projects_opens_more_menu_once(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class DummyPage:
        def __init__(self) -> None:
            self.waits: list[int] = []

        async def wait_for_timeout(self, ms):
            self.waits.append(ms)
            return None

    page = DummyPage()

    discovered = iter(
        [
            [{"name": "Alpha", "url": "https://chatgpt.com/g/g-p-alpha-demo/project"}],
            [
                {"name": "Alpha", "url": "https://chatgpt.com/g/g-p-alpha-demo/project"},
                {"name": "Beta", "url": "https://chatgpt.com/g/g-p-beta-demo/project"},
            ],
        ]
    )
    moved = iter([False])
    opened: list[bool] = []

    async def fake_collect(_page):
        return next(discovered)

    async def fake_scroll(_page):
        return next(moved)

    async def fake_open_more(_page):
        opened.append(True)
        return True

    client._collect_sidebar_projects = fake_collect
    client._scroll_project_sidebar_step = fake_scroll
    client._open_more_projects_menu = fake_open_more

    import asyncio

    result = asyncio.run(client._collect_all_sidebar_projects(page, label="project-list", max_scroll_rounds=3))
    assert [item["name"] for item in result] == ["Alpha", "Beta"]
    assert opened == [True]

