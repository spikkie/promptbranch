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



def test_determine_project_discovery_mode_prefers_more_when_sidebar_project_controls_missing(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    async def fake_find_visible_locator(page, selectors, label=None, timeout_ms=0):
        if label == "project-discovery-entrypoint":
            return None
        if label == "project-more-entrypoint":
            return object()
        return None

    client._find_visible_locator = fake_find_visible_locator

    import asyncio

    mode = asyncio.run(client._determine_project_discovery_mode(page=object()))
    assert mode == "more-first"


def test_determine_project_discovery_mode_falls_back_to_sidebar_when_more_missing(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    async def fake_find_visible_locator(page, selectors, label=None, timeout_ms=0):
        return None

    client._find_visible_locator = fake_find_visible_locator

    import asyncio

    mode = asyncio.run(client._determine_project_discovery_mode(page=object()))
    assert mode == "sidebar-first"


def test_is_snorlax_sidebar_url_matches_sidebar_endpoint(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    assert client._is_snorlax_sidebar_url("https://chatgpt.com/backend-api/gizmos/snorlax/sidebar?limit=20") is True
    assert client._is_snorlax_sidebar_url("https://chatgpt.com/backend-api/gizmos/snorlax/upsert") is False


def test_debug_project_list_operation_creates_nested_artifacts(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client._artifact_dir = tmp_path / "debug_artifacts"
    client._artifact_dir.mkdir(parents=True, exist_ok=True)

    class DummyPage:
        url = "https://chatgpt.com/"

        async def wait_for_timeout(self, ms):
            return None

        async def screenshot(self, path, full_page=True):
            Path(path).write_bytes(b"png")
            return None

        async def content(self):
            return "<html></html>"

        async def title(self):
            return "ChatGPT"

    page = DummyPage()

    async def fake_ensure_logged_in(page, context):
        return None

    async def fake_goto(page, url, label=None):
        return None

    async def fake_sidebar(page):
        return None

    async def fake_determine(page):
        return "more-first"

    async def fake_open_more(page):
        return True

    async def fake_expand(page):
        return False

    async def fake_collect(page):
        return []

    async def fake_scroll(page):
        return False

    async def fake_collect_all(page, label, max_scroll_rounds=40):
        return []

    async def fake_safe_page_url(page):
        return "https://chatgpt.com/"

    async def fake_snapshot(page):
        return []

    client.ensure_logged_in = fake_ensure_logged_in
    client._goto = fake_goto
    client._ensure_sidebar_open = fake_sidebar
    client._determine_project_discovery_mode = fake_determine
    client._open_more_projects_menu = fake_open_more
    client._expand_projects_section = fake_expand
    client._collect_sidebar_projects = fake_collect
    client._scroll_project_sidebar_step = fake_scroll
    client._collect_all_sidebar_projects = fake_collect_all
    client._safe_page_url = fake_safe_page_url
    client._project_link_debug_snapshot = fake_snapshot
    client._dialog_like_debug_snapshot = fake_snapshot
    client._scrollable_debug_snapshot = fake_snapshot
    client._more_candidate_debug_snapshot = fake_snapshot

    import asyncio

    result = asyncio.run(
        client._debug_project_list_operation(
            context=None,
            page=page,
            scroll_rounds=1,
            wait_ms=0,
            manual_pause=False,
            keep_open=False,
        )
    )

    artifact_dir = Path(result["artifact_dir"])
    assert artifact_dir.exists()
    assert (artifact_dir / "01-before-discovery.png").exists()
    assert (artifact_dir / "summary.json").exists()
    assert result["discovery_mode"] == "more-first"


def test_extract_projects_from_snorlax_sidebar_payload_normalizes_projects(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    payload = {
        "items": [
            {
                "gizmo": {
                    "gizmo": {
                        "id": "g-p-alpha123",
                        "short_url": "g-p-alpha123-alpha-project",
                        "display": {"name": "Alpha Project"},
                    }
                }
            },
            {
                "gizmo": {
                    "gizmo": {
                        "id": "g-p-beta456",
                        "short_url": "g-p-beta456-beta-project",
                        "display": {"name": "Beta Project"},
                    }
                }
            },
        ],
        "cursor": "next-cursor",
    }

    projects, cursor = client._extract_projects_from_snorlax_sidebar_payload(payload)
    assert cursor == "next-cursor"
    assert projects == [
        {"name": "Alpha Project", "url": "https://chatgpt.com/g/g-p-alpha123-alpha-project/project"},
        {"name": "Beta Project", "url": "https://chatgpt.com/g/g-p-beta456-beta-project/project"},
    ]


def test_collect_all_projects_via_snorlax_sidebar_follows_cursor(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    responses = iter([
        {
            "status": 200,
            "payload": {
                "items": [
                    {"gizmo": {"gizmo": {"short_url": "g-p-alpha123-alpha-project", "display": {"name": "Alpha Project"}}}},
                    {"gizmo": {"gizmo": {"short_url": "g-p-beta456-beta-project", "display": {"name": "Beta Project"}}}},
                ],
                "cursor": "cursor-2",
            },
        },
        {
            "status": 200,
            "payload": {
                "items": [
                    {"gizmo": {"gizmo": {"short_url": "g-p-gamma789-gamma-project", "display": {"name": "Gamma Project"}}}},
                ],
                "cursor": None,
            },
        },
    ])
    seen_cursors: list[str | None] = []

    async def fake_fetch(page, *, cursor=None, limit=20, conversations_per_gizmo=5):
        seen_cursors.append(cursor)
        return next(responses)

    client._fetch_snorlax_sidebar_page = fake_fetch

    import asyncio

    projects = asyncio.run(client._collect_all_projects_via_snorlax_sidebar(page=object(), label="project-list"))
    assert seen_cursors == [None, "cursor-2"]
    assert [item["name"] for item in projects] == ["Alpha Project", "Beta Project", "Gamma Project"]


def test_list_projects_operation_prefers_snorlax_sidebar_enumeration(tmp_path: Path) -> None:
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

    async def fake_collect_snorlax(page, *, label, max_pages=25):
        return [
            {"name": "Alpha", "url": "https://chatgpt.com/g/g-p-alpha-demo/project"},
            {"name": "Current", "url": "https://chatgpt.com/g/g-p-current-demo/project"},
        ]

    async def fake_prepare(*args, **kwargs):
        raise AssertionError("DOM discovery should not run when snorlax enumeration succeeds")

    async def fake_safe_page_url(page):
        return "https://chatgpt.com/"

    client.ensure_logged_in = fake_ensure_logged_in
    client._goto = fake_goto
    client._ensure_sidebar_open = fake_sidebar
    client._collect_all_projects_via_snorlax_sidebar = fake_collect_snorlax
    client._prepare_project_discovery = fake_prepare
    client._safe_page_url = fake_safe_page_url

    import asyncio

    result = asyncio.run(client._list_projects_operation(context=None, page=page, keep_open=False))
    assert result["count"] == 2
    assert [item["name"] for item in result["projects"]] == ["Alpha", "Current"]
    assert any(item["is_current"] for item in result["projects"])
