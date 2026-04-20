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
