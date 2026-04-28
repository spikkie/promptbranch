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



def test_collect_all_projects_via_snorlax_sidebar_keeps_successful_page_when_later_page_is_unauthorized(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    responses = iter([
        {
            "status": 200,
            "used_authorization": True,
            "payload": {
                "items": [
                    {"gizmo": {"gizmo": {"short_url": "g-p-alpha123-alpha-project", "display": {"name": "Alpha Project"}}}},
                ],
                "cursor": "cursor-2",
            },
        },
        {
            "status": 401,
            "used_authorization": True,
            "payload": {
                "detail": {"message": "Unauthorized - Access token is missing"},
            },
        },
    ])

    async def fake_fetch(page, *, cursor=None, limit=20, conversations_per_gizmo=5):
        return next(responses)

    client._fetch_snorlax_sidebar_page = fake_fetch

    import asyncio

    projects = asyncio.run(client._collect_all_projects_via_snorlax_sidebar(page=object(), label="project-list"))
    assert projects == [
        {"name": "Alpha Project", "url": "https://chatgpt.com/g/g-p-alpha123-alpha-project/project"},
    ]


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




def test_list_project_chats_operation_falls_back_to_project_home_dom_when_history_is_empty(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    page = object()

    async def fake_ensure_logged_in(page, context):
        return None

    async def fake_goto(page, url, label=None):
        return None

    async def fake_open_chats_tab(page):
        return None

    async def fake_collect_dom(page, *, project_url, label):
        assert project_url == "https://chatgpt.com/g/g-p-current-demo/project"
        return [
            {
                "id": "chat-dom-1",
                "title": "Azure DevOps Engineer Role",
                "conversation_url": "https://chatgpt.com/g/g-p-current-demo/c/chat-dom-1",
                "create_time": None,
                "update_time": None,
            }
        ]

    async def fake_collect_history(page, *, project_url, label):
        return []

    async def fake_safe_page_url(page):
        return "https://chatgpt.com/g/g-p-current-demo/project"

    client.ensure_logged_in = fake_ensure_logged_in
    client._goto = fake_goto
    client._open_project_chats_tab = fake_open_chats_tab
    client._collect_project_chats_from_home_dom = fake_collect_dom
    client._collect_all_project_chats = fake_collect_history
    client._safe_page_url = fake_safe_page_url
    client.config.project_url = "https://chatgpt.com/g/g-p-current-demo/project"

    import asyncio

    result = asyncio.run(client._list_project_chats_operation(context=None, page=page, keep_open=False))

    assert result["count"] == 1
    assert result["chats"][0]["title"] == "Azure DevOps Engineer Role"


def test_merge_project_chat_lists_prefers_primary_and_adds_missing_secondary_fields(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    merged = client._merge_project_chat_lists(
        [
            {
                "id": "chat-1",
                "title": "Primary title",
                "conversation_url": "https://chatgpt.com/g/g-p-current-demo/c/chat-1",
                "create_time": None,
                "update_time": None,
            }
        ],
        [
            {
                "id": "chat-1",
                "title": "Secondary title",
                "conversation_url": "https://chatgpt.com/g/g-p-current-demo/c/chat-1",
                "preview": "Secondary preview",
                "create_time": None,
                "update_time": None,
            },
            {
                "id": "chat-2",
                "title": "Only secondary",
                "conversation_url": "https://chatgpt.com/g/g-p-current-demo/c/chat-2",
                "create_time": None,
                "update_time": None,
            },
        ],
    )

    assert merged[0]["title"] == "Primary title"
    assert merged[0]["preview"] == "Secondary preview"
    assert merged[1]["id"] == "chat-2"

def test_extract_project_chats_from_conversations_payload_requires_matching_project_id(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    payload = {
        "items": [
            {
                "id": "chat-project-1",
                "title": "Project chat",
                "conversation_template_id": "g-p-current",
            },
            {
                "id": "chat-project-slug",
                "title": "Project chat slug id",
                "conversation_template_id": "g-p-current-demo",
            },
            {
                "id": "chat-global-1",
                "title": "Global chat without project id",
            },
            {
                "id": "chat-other-1",
                "title": "Other project chat",
                "conversation_template_id": "g-p-other",
            },
        ]
    }

    chats = client._extract_project_chats_from_conversations_payload(
        payload,
        project_id="g-p-current",
        project_url="https://chatgpt.com/g/g-p-current-demo/project",
    )

    assert chats == [
        {
            "id": "chat-project-1",
            "title": "Project chat",
            "conversation_url": "https://chatgpt.com/g/g-p-current-demo/c/chat-project-1",
            "create_time": None,
            "update_time": None,
        },
        {
            "id": "chat-project-slug",
            "title": "Project chat slug id",
            "conversation_url": "https://chatgpt.com/g/g-p-current-demo/c/chat-project-slug",
            "create_time": None,
            "update_time": None,
        }
    ]




def test_extract_project_chats_from_snorlax_sidebar_payload_matches_project(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    payload = {
        "cursor": "next-cursor",
        "items": [
            {
                "gizmo": {
                    "gizmo": {
                        "id": "g-p-other",
                        "display": {"name": "Other"},
                    }
                },
                "conversations": {
                    "items": [
                        {"id": "chat-other", "title": "Other chat"},
                    ]
                },
            },
            {
                "gizmo": {
                    "gizmo": {
                        "id": "g-p-current-demo",
                        "display": {"name": "Current"},
                    }
                },
                "conversations": {
                    "items": [
                        {
                            "id": "chat-1",
                            "title": "Azure DevOps Engineer Role",
                            "create_time": "2026-04-03T00:00:00Z",
                            "update_time": "2026-04-03T01:00:00Z",
                        },
                        {
                            "id": "chat-2",
                            "title": "Another chat",
                        },
                    ]
                },
            },
        ],
    }

    chats, cursor, found_project = client._extract_project_chats_from_snorlax_sidebar_payload(
        payload,
        project_id="g-p-current",
        project_url="https://chatgpt.com/g/g-p-current-demo/project",
    )

    assert found_project is True
    assert cursor == "next-cursor"
    assert chats == [
        {
            "id": "chat-1",
            "title": "Azure DevOps Engineer Role",
            "conversation_url": "https://chatgpt.com/g/g-p-current-demo/c/chat-1",
            "create_time": "2026-04-03T00:00:00Z",
            "update_time": "2026-04-03T01:00:00Z",
        },
        {
            "id": "chat-2",
            "title": "Another chat",
            "conversation_url": "https://chatgpt.com/g/g-p-current-demo/c/chat-2",
            "create_time": None,
            "update_time": None,
        },
    ]


def test_collect_project_chats_via_snorlax_sidebar_follows_cursor_after_target_project(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    page = object()
    calls: list[str | None] = []

    async def fake_fetch(page, *, cursor=None, limit=20, conversations_per_gizmo=100):
        calls.append(cursor)
        if cursor is None:
            return {
                "status": 200,
                "used_authorization": True,
                "payload": {
                    "cursor": "cursor-2",
                    "items": [
                        {
                            "gizmo": {"gizmo": {"id": "g-p-current-demo"}},
                            "conversations": {
                                "items": [
                                    {"id": "chat-1", "title": "First visible task"},
                                ]
                            },
                        }
                    ],
                },
            }
        if cursor == "cursor-2":
            return {
                "status": 200,
                "used_authorization": True,
                "payload": {
                    "cursor": None,
                    "items": [
                        {
                            "gizmo": {"gizmo": {"id": "g-p-current-demo"}},
                            "conversations": {
                                "items": [
                                    {"id": "chat-2", "title": "Task below scroll fold"},
                                ]
                            },
                        }
                    ],
                },
            }
        raise AssertionError(f"unexpected cursor: {cursor}")

    client._fetch_snorlax_sidebar_page = fake_fetch

    import asyncio

    chats = asyncio.run(
        client._collect_project_chats_via_snorlax_sidebar(
            page,
            project_url="https://chatgpt.com/g/g-p-current-demo/project",
            label="test-snorlax",
        )
    )

    assert calls == [None, "cursor-2"]
    assert [chat["id"] for chat in chats] == ["chat-1", "chat-2"]


def test_list_project_chats_operation_uses_snorlax_sidebar_when_history_and_dom_are_empty(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    page = object()

    async def fake_ensure_logged_in(page, context):
        return None

    async def fake_goto(page, url, label=None):
        return None

    async def fake_open_chats_tab(page):
        return None

    async def fake_collect_snorlax(page, *, project_url, label):
        assert project_url == "https://chatgpt.com/g/g-p-current-demo/project"
        return [
            {
                "id": "chat-snorlax-1",
                "title": "Azure DevOps Engineer Role",
                "conversation_url": "https://chatgpt.com/g/g-p-current-demo/c/chat-snorlax-1",
                "create_time": None,
                "update_time": None,
            }
        ]

    async def fake_collect_dom(page, *, project_url, label):
        return []

    async def fake_collect_history(page, *, project_url, label):
        raise AssertionError("conversation history fallback should not run when snorlax/dom already found chats")

    async def fake_safe_page_url(page):
        return "https://chatgpt.com/g/g-p-current-demo/project"

    client.ensure_logged_in = fake_ensure_logged_in
    client._goto = fake_goto
    client._open_project_chats_tab = fake_open_chats_tab
    client._collect_project_chats_via_snorlax_sidebar = fake_collect_snorlax
    client._collect_project_chats_from_home_dom = fake_collect_dom
    client._collect_all_project_chats = fake_collect_history
    client._safe_page_url = fake_safe_page_url
    client.config.project_url = "https://chatgpt.com/g/g-p-current-demo/project"

    import asyncio

    result = asyncio.run(client._list_project_chats_operation(context=None, page=page, keep_open=False))

    assert result["count"] == 1
    assert result["chats"][0]["title"] == "Azure DevOps Engineer Role"

def test_list_project_chats_operation_uses_current_project_conversation_when_indexes_lag(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    page = object()

    async def fake_ensure_logged_in(page, context):
        return None

    async def fake_goto(page, url, label=None):
        return None

    async def fake_open_chats_tab(page):
        return None

    async def fake_collect_snorlax(page, *, project_url, label):
        return []

    async def fake_collect_dom(page, *, project_url, label):
        return []

    async def fake_collect_history(page, *, project_url, label):
        raise AssertionError("history fallback should not run when the current project conversation is known")

    urls = iter([
        "https://chatgpt.com/g/g-p-current-demo/c/chat-current-1",
        "https://chatgpt.com/g/g-p-current-demo/project",
    ])

    async def fake_safe_page_url(page):
        return next(urls)

    async def fake_fetch_detail(page, *, conversation_id):
        assert conversation_id == "chat-current-1"
        return {
            "status": 200,
            "payload": {
                "title": "Freshly created task",
                "create_time": "2026-04-27T12:00:00Z",
                "update_time": "2026-04-27T12:01:00Z",
            },
        }

    client.ensure_logged_in = fake_ensure_logged_in
    client._goto = fake_goto
    client._open_project_chats_tab = fake_open_chats_tab
    client._collect_project_chats_via_snorlax_sidebar = fake_collect_snorlax
    client._collect_project_chats_from_home_dom = fake_collect_dom
    client._collect_all_project_chats = fake_collect_history
    client._safe_page_url = fake_safe_page_url
    client._fetch_conversation_detail = fake_fetch_detail
    client.config.project_url = "https://chatgpt.com/g/g-p-current-demo/project"

    import asyncio

    result = asyncio.run(client._list_project_chats_operation(context=None, page=page, keep_open=False))

    assert result["count"] == 1
    assert result["chats"][0]["id"] == "chat-current-1"
    assert result["chats"][0]["title"] == "Freshly created task"
    assert result["chats"][0]["source"] == "current_page"
    assert result["source_counts"]["current_page"] == 1
    assert result["history_fallback_used"] is False


def test_is_conversation_history_url_accepts_detail_endpoint(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    assert client._is_conversation_history_url('https://chatgpt.com/backend-api/conversation/abc123') is True
    assert client._is_conversation_history_url('https://chatgpt.com/backend-api/conversations?offset=0') is True
    assert client._is_conversation_history_url('https://chatgpt.com/backend-api/gizmos/snorlax/sidebar') is False


def test_wait_for_visible_locator_checks_rate_limit_modal_between_polls(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class DummyPage:
        def __init__(self) -> None:
            self.waits: list[int] = []

        async def wait_for_timeout(self, ms):
            self.waits.append(ms)
            return None

    page = DummyPage()
    calls: list[str] = []
    finds = iter([None, object()])

    async def fake_wait(page, *, label: str, timeout_ms: int | None = None):
        calls.append(label)
        return False

    async def fake_find(page, selectors, *, label: str, timeout_ms: int = 1500):
        return next(finds)

    client._wait_for_rate_limit_modal_to_clear = fake_wait
    client._find_visible_locator = fake_find

    import asyncio

    locator = asyncio.run(
        client._wait_for_visible_locator(
            page,
            ['button:has-text("Create")'],
            label='project-create-button',
            total_timeout_ms=2000,
            poll_interval_ms=25,
            visibility_timeout_ms=10,
        )
    )

    assert locator is not None
    assert calls == ['project-create-button-wait', 'project-create-button-wait']
    assert page.waits == [25]
