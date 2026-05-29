import json
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



async def _async_tuple(value):
    return value

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

    async def fake_fetch(page, *, cursor=None, limit=20, conversations_per_gizmo=20):
        assert conversations_per_gizmo == 20
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

def test_collect_project_chats_via_project_conversations_endpoint_uses_project_endpoint_pagination(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    page = object()
    calls: list[str | None] = []

    async def fake_fetch(page, *, project_id, cursor=None, limit=50):
        assert project_id == "g-p-current"
        assert limit == 50
        calls.append(cursor)
        if cursor is None:
            return {
                "status": 200,
                "used_authorization": True,
                "payload": {
                    "items": [
                        {"id": "chat-1", "title": "Task 1"},
                    ],
                    "cursor": "next-page",
                },
            }
        if cursor == "next-page":
            return {
                "status": 200,
                "used_authorization": True,
                "payload": {
                    "items": [
                        {"id": "chat-21", "title": "Task 21"},
                    ],
                },
            }
        raise AssertionError(f"unexpected cursor: {cursor}")

    client._fetch_project_conversations_page = fake_fetch

    import asyncio

    chats = asyncio.run(
        client._collect_project_chats_via_project_conversations_endpoint(
            page,
            project_url="https://chatgpt.com/g/g-p-current-demo/project",
            label="test-project-endpoint",
        )
    )

    assert calls == [None, "next-page"]
    assert [chat["id"] for chat in chats] == ["chat-1", "chat-21"]
    assert all(chat["source"] == "project_endpoint" for chat in chats)


def test_list_project_chats_operation_supplements_snorlax_with_history(tmp_path: Path) -> None:
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
        return [
            {
                "id": "chat-history-2",
                "title": "Below scroll fold",
                "conversation_url": "https://chatgpt.com/g/g-p-current-demo/c/chat-history-2",
                "create_time": None,
                "update_time": None,
            }
        ]

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

    assert result["count"] == 2
    assert [chat["id"] for chat in result["chats"]] == ["chat-snorlax-1", "chat-history-2"]
    assert result["source_counts"]["history"] == 1
    assert result["history_supplement_used"] is True


def test_list_project_chats_operation_skips_global_history_when_project_endpoint_returns_rows(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    page = object()
    history_called = False

    async def fake_ensure_logged_in(page, context):
        return None

    async def fake_goto(page, url, label=None):
        return None

    async def fake_open_chats_tab(page):
        return True

    async def fake_collect_snorlax(page, *, project_url, label):
        return [
            {
                "id": "chat-snorlax-1",
                "title": "Visible task",
                "conversation_url": "https://chatgpt.com/g/g-p-current-demo/c/chat-snorlax-1",
            }
        ]

    async def fake_collect_project_endpoint(page, *, project_url, label):
        return [
            {
                "id": "chat-snorlax-1",
                "title": "Visible task",
                "conversation_url": "https://chatgpt.com/g/g-p-current-demo/c/chat-snorlax-1",
                "source": "project_endpoint",
            },
            {
                "id": "chat-21",
                "title": "Task 21",
                "conversation_url": "https://chatgpt.com/g/g-p-current-demo/c/chat-21",
                "source": "project_endpoint",
            },
        ]

    async def fake_collect_dom(page, *, project_url, label):
        return []

    async def fake_collect_history(page, *, project_url, label):
        nonlocal history_called
        history_called = True
        return []

    async def fake_safe_page_url(page):
        return "https://chatgpt.com/g/g-p-current-demo/project"

    client.ensure_logged_in = fake_ensure_logged_in
    client._goto = fake_goto
    client._open_project_chats_tab = fake_open_chats_tab
    client._collect_project_chats_via_snorlax_sidebar = fake_collect_snorlax
    client._collect_project_chats_via_project_conversations_endpoint = fake_collect_project_endpoint
    client._collect_project_chats_from_home_dom = fake_collect_dom
    client._collect_all_project_chats = fake_collect_history
    client._safe_page_url = fake_safe_page_url
    client.config.project_url = "https://chatgpt.com/g/g-p-current-demo/project"

    import asyncio

    result = asyncio.run(client._list_project_chats_operation(context=None, page=page, keep_open=False))

    assert history_called is False
    assert result["count"] == 2
    assert [chat["id"] for chat in result["chats"]] == ["chat-snorlax-1", "chat-21"]
    assert result["source_counts"]["project_endpoint"] == 2
    assert result["history_supplement_used"] is False
    assert result["history_fallback_skipped"] is True
    assert result["history_supplement_skipped_reason"] == "project_endpoint_available"

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
        return []

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
    assert result["history_fallback_used"] is True



def test_goto_skips_noop_navigation_to_avoid_history_reload(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class DummyPage:
        url = "https://chatgpt.com/g/g-p-current-demo/project?tab=sources"

        def __init__(self) -> None:
            self.goto_calls: list[tuple[str, str]] = []
            self.titles = 0

        async def goto(self, url: str, *, wait_until: str):
            self.goto_calls.append((url, wait_until))

        async def title(self):
            self.titles += 1
            return "Project"

    page = DummyPage()
    waits: list[str] = []

    async def fake_wait(page, *, label: str, timeout_ms: int | None = None):
        waits.append(label)
        return False

    client._wait_for_rate_limit_modal_to_clear = fake_wait

    import asyncio

    asyncio.run(client._goto(page, "https://chatgpt.com/g/g-p-current-demo/project?tab=sources", label="project-source-remove-home"))

    assert page.goto_calls == []
    assert waits == ["project-source-remove-home"]
    telemetry = client._rate_limit_telemetry_snapshot()
    assert telemetry["navigation_noop_skip_count"] == 1
    assert telemetry["service_rate_limit_events"] == []


def test_goto_does_not_skip_explicit_refresh_navigation(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class DummyPage:
        url = "https://chatgpt.com/g/g-p-current-demo/project?tab=sources"

        def __init__(self) -> None:
            self.goto_calls: list[tuple[str, str]] = []

        async def goto(self, url: str, *, wait_until: str):
            self.goto_calls.append((url, wait_until))
            self.url = url

        async def title(self):
            return "Project"

    page = DummyPage()

    async def fake_wait(page, *, label: str, timeout_ms: int | None = None):
        return False

    client._wait_for_rate_limit_modal_to_clear = fake_wait

    import asyncio

    asyncio.run(client._goto(page, "https://chatgpt.com/g/g-p-current-demo/project?tab=sources", label="project-source-add-persistence-refresh"))

    assert page.goto_calls == [("https://chatgpt.com/g/g-p-current-demo/project?tab=sources", "domcontentloaded")]
    assert client._rate_limit_telemetry_snapshot()["navigation_noop_skip_count"] == 0


def test_list_project_chats_skips_history_supplement_during_cooldown_when_indexed_rows_exist(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client._write_rate_limit_cooldown_until(__import__("time").time() + 120.0)
    page = object()
    history_called = False

    async def fake_ensure_logged_in(page, context):
        return None

    async def fake_goto(page, url, label=None):
        return None

    async def fake_open_chats_tab(page):
        return True

    async def fake_collect_snorlax(page, *, project_url, label):
        return [
            {
                "id": "chat-snorlax-1",
                "title": "Visible task",
                "conversation_url": "https://chatgpt.com/g/g-p-current-demo/c/chat-snorlax-1",
                "source": "snorlax",
            }
        ]

    async def fake_collect_project_endpoint(page, *, project_url, label):
        return []

    async def fake_collect_dom(page, *, project_url, label):
        return []

    async def fake_collect_history(page, *, project_url, label):
        nonlocal history_called
        history_called = True
        return []

    async def fake_safe_page_url(page):
        return "https://chatgpt.com/g/g-p-current-demo/project"

    client.ensure_logged_in = fake_ensure_logged_in
    client._goto = fake_goto
    client._open_project_chats_tab = fake_open_chats_tab
    client._collect_project_chats_via_snorlax_sidebar = fake_collect_snorlax
    client._collect_project_chats_via_project_conversations_endpoint = fake_collect_project_endpoint
    client._collect_project_chats_from_home_dom = fake_collect_dom
    client._collect_all_project_chats = fake_collect_history
    client._safe_page_url = fake_safe_page_url
    client.config.project_url = "https://chatgpt.com/g/g-p-current-demo/project"

    import asyncio

    result = asyncio.run(client._list_project_chats_operation(context=None, page=page, keep_open=False))

    assert history_called is False
    assert result["count"] == 1
    assert result["history_fallback_skipped"] is True
    assert result["history_supplement_used"] is False
    assert result["history_supplement_skipped_reason"] == "conversation_history_cooldown_active_indexed_sources_available"
    telemetry = client._rate_limit_telemetry_snapshot()
    assert telemetry["conversation_history_fetch_skipped_count"] >= 1
    assert telemetry["conversation_history_cooldown_skip_count"] >= 1


def test_fetch_conversations_page_skips_during_cooldown(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client._write_rate_limit_cooldown_until(__import__("time").time() + 120.0)

    class DummyPage:
        async def evaluate(self, *_args, **_kwargs):
            raise AssertionError("conversation history fetch should have been skipped")

    import asyncio

    result = asyncio.run(client._fetch_conversations_page(DummyPage(), offset=28, limit=28, label="chat-list"))

    assert result["skipped"] is True
    assert result["status"] == "skipped_cooldown"
    assert result["skip_reason"] == "conversation_history_cooldown_active"
    telemetry = client._rate_limit_telemetry_snapshot()
    assert telemetry["conversation_history_fetch_attempt_count"] == 0
    assert telemetry["conversation_history_fetch_skipped_count"] == 1

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


def test_list_project_chats_operation_does_not_count_sidebar_dom_when_chats_tab_inactive(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    page = object()

    async def fake_ensure_logged_in(page, context):
        return None

    async def fake_goto(page, url, label=None):
        return None

    async def fake_open_chats_tab(page):
        return False

    async def fake_collect_snorlax(page, *, project_url, label):
        return []

    async def fake_collect_dom(page, *, project_url, label):  # pragma: no cover - must not be called
        raise AssertionError("DOM collection should be skipped when Chats tab is inactive")

    async def fake_collect_history(page, *, project_url, label):
        return []

    async def fake_safe_page_url(page):
        return "https://chatgpt.com/g/g-p-current-demo/project?tab=sources"

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

    assert result["ok"] is True
    assert result["count"] == 0
    assert result["source_counts"]["dom"] == 0
    assert result["chats_tab_active"] is False


def test_collect_all_project_chats_uses_detail_probe_when_history_items_lack_project_id(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class DummyPage:
        async def wait_for_timeout(self, ms):
            return None

    page = DummyPage()

    async def fake_fetch_conversations_page(page, *, offset=0, limit=100, order="updated"):
        assert offset == 0
        return {
            "status": 200,
            "payload": {
                "items": [
                    {"id": "chat-other", "title": "Other project"},
                    {"id": "chat-target", "title": "Target project"},
                ]
            },
            "used_authorization": True,
        }

    async def fake_fetch_conversation_detail(page, *, conversation_id):
        if conversation_id == "chat-target":
            return {
                "status": 200,
                "payload": {
                    "title": "Target detail title",
                    "conversation_template_id": "g-p-current-demo",
                    "update_time": "2026-04-28T12:00:00Z",
                },
            }
        return {"status": 200, "payload": {"title": "Other detail", "conversation_template_id": "g-p-other-demo"}}

    client._fetch_conversations_page = fake_fetch_conversations_page
    client._fetch_conversation_detail = fake_fetch_conversation_detail

    import asyncio

    result = asyncio.run(
        client._collect_all_project_chats(
            page,
            project_url="https://chatgpt.com/g/g-p-current-demo/project",
            label="chat-list",
            max_detail_probes=5,
            detail_probe_delay_ms=0,
        )
    )

    assert len(result) == 1
    assert result[0]["id"] == "chat-target"
    assert result[0]["title"] == "Target detail title"
    assert result[0]["source"] == "history_detail"


def test_list_project_chats_operation_reports_history_detail_source_count(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    page = object()

    async def fake_ensure_logged_in(page, context):
        return None

    async def fake_goto(page, url, label=None):
        return None

    async def fake_open_chats_tab(page):
        return True

    async def fake_collect_snorlax(page, *, project_url, label):
        return []

    async def fake_collect_dom(page, *, project_url, label):
        return []

    async def fake_collect_history(page, *, project_url, label):
        return [
            {
                "id": "chat-target",
                "title": "Target detail title",
                "conversation_url": "https://chatgpt.com/g/g-p-current-demo/c/chat-target",
                "source": "history_detail",
            }
        ]

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
    assert result["source_counts"]["history"] == 0
    assert result["source_counts"]["history_detail"] == 1


def test_fetch_snorlax_sidebar_page_clamps_conversations_per_gizmo(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class FakePage:
        async def evaluate(self, _script, args):
            assert args["conversationsPerGizmo"] == 20
            assert args["limit"] == 100
            return {
                "ok": True,
                "status": 200,
                "url": "https://chatgpt.com/backend-api/gizmos/snorlax/sidebar",
                "text": "{}",
                "headers": {"content-type": "application/json"},
                "usedAuthorization": True,
            }

    import asyncio

    result = asyncio.run(
        client._fetch_snorlax_sidebar_page(
            FakePage(),
            conversations_per_gizmo=100,
            limit=500,
        )
    )

    assert result["status"] == 200
    assert result["payload"] == {}


def test_conversation_history_items_from_payload_handles_nested_edges(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    payload = {
        "data": {
            "gizmo": {
                "conversations": {
                    "edges": [
                        {
                            "node": {
                                "id": "68b74149-22a0-832f-98f2-8787319c2eb7",
                                "title": "Nested project task",
                                "create_time": "2025-09-02T10:00:00Z",
                            },
                            "cursor": "cursor-1",
                        }
                    ]
                }
            }
        }
    }

    items = client._conversation_history_items_from_payload(payload)
    assert len(items) == 1
    assert items[0]["id"] == "68b74149-22a0-832f-98f2-8787319c2eb7"
    assert items[0]["title"] == "Nested project task"


def test_extract_project_chats_prefers_nested_conversation_cursor(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    payload = {
        "cursor": "root-project-cursor",
        "items": [
            {
                "gizmo": {"gizmo": {"id": "g-p-current-demo"}},
                "conversations": {
                    "items": [
                        {"id": "chat-1", "title": "Task 1"},
                    ],
                    "cursor": "nested-conversation-cursor",
                },
            }
        ],
    }

    chats, cursor, found_project = client._extract_project_chats_from_snorlax_sidebar_payload(
        payload,
        project_id="g-p-current",
        project_url="https://chatgpt.com/g/g-p-current-demo/project",
    )

    assert found_project is True
    assert [chat["id"] for chat in chats] == ["chat-1"]
    assert cursor == "nested-conversation-cursor"


def test_collect_project_endpoint_exposes_diagnostics_when_empty(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    page = object()

    async def fake_fetch(page, *, project_id, cursor=None, limit=50):
        assert limit == 50
        return {
            "status": 200,
            "url": "https://chatgpt.com/backend-api/gizmos/g-p-current/conversations?limit=50",
            "used_authorization": True,
            "payload": {"data": {"unexpected": []}},
            "text": '{"data":{"unexpected":[]}}',
        }

    client._fetch_project_conversations_page = fake_fetch

    import asyncio

    chats = asyncio.run(
        client._collect_project_chats_via_project_conversations_endpoint(
            page,
            project_url="https://chatgpt.com/g/g-p-current-demo/project",
            label="test-project-endpoint",
        )
    )

    assert chats == []
    diagnostics = getattr(client, "_last_project_conversations_endpoint_diagnostics")
    assert diagnostics[0]["status"] == 200
    assert diagnostics[0]["discovered_count"] == 0
    assert "payload_shape" in diagnostics[0]


def test_fetch_project_conversations_page_clamps_limit_to_50(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class FakePage:
        async def evaluate(self, _script, args):
            assert args["limit"] == 50
            assert args["cursor"] is None
            assert args["projectId"] == "g-p-current"
            return {
                "ok": True,
                "status": 200,
                "url": "https://chatgpt.com/backend-api/gizmos/g-p-current/conversations?limit=50",
                "text": "{}",
                "usedAuthorization": True,
            }

    import asyncio

    result = asyncio.run(
        client._fetch_project_conversations_page(
            FakePage(),
            project_id="g-p-current",
            limit=100,
        )
    )

    assert result["status"] == 200
    assert result["payload"] == {}


def test_goto_skips_same_conversation_ask_navigation_by_default(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class DummyPage:
        url = "https://chatgpt.com/g/g-p-current-demo/c/chat-1"

        def __init__(self) -> None:
            self.goto_calls: list[tuple[str, str]] = []

        async def goto(self, url: str, *, wait_until: str):
            self.goto_calls.append((url, wait_until))
            self.url = url

        async def title(self):
            return "Chat"

    page = DummyPage()

    async def fake_wait(page, *, label: str, timeout_ms: int | None = None):
        return False

    client._wait_for_rate_limit_modal_to_clear = fake_wait

    import asyncio

    result = asyncio.run(client._goto(page, "https://chatgpt.com/g/g-p-current-demo/c/chat-1", label="chat-home-after-login"))

    assert page.goto_calls == []
    assert result["mode"] == "same_url_skip"
    assert result["skipped"] is True
    assert client._rate_limit_telemetry_snapshot()["navigation_noop_skip_count"] == 1


def test_ensure_target_conversation_hydrated_forces_reload_before_failure(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class DummyPage:
        url = "https://chatgpt.com/g/g-p-current-demo/c/chat-1"

        def __init__(self) -> None:
            self.goto_calls: list[tuple[str, str]] = []
            self.waits: list[int] = []

        async def goto(self, url: str, *, wait_until: str):
            self.goto_calls.append((url, wait_until))
            self.url = url

        async def wait_for_timeout(self, ms: int):
            self.waits.append(ms)

    page = DummyPage()

    async def fake_turn_state(page, *, prompt=None):
        return {"count": 0, "generic_turns": {"count": 0}, "last_text_length": 0}

    async def fake_wait_rate_limit(page, *, label: str, timeout_ms: int | None = None):
        return False

    async def fake_has_chat_input(page):
        return False

    client._capture_user_turn_state = fake_turn_state
    client._wait_for_rate_limit_modal_to_clear = fake_wait_rate_limit
    client._has_chat_input = fake_has_chat_input

    import asyncio

    result = asyncio.run(
        client._ensure_target_conversation_hydrated(
            page,
            target_url="https://chatgpt.com/g/g-p-current-demo/c/chat-1",
            label="chat-home-after-login",
            timeout_ms=1,
            poll_interval_ms=1,
        )
    )

    assert result["status"] == "target_conversation_not_hydrated_before_submit"
    assert result["reload_performed"] is True
    assert result["reload_count"] == 2
    assert result["max_reload_attempts"] == 2
    assert result["final_user_turn_count"] == 0
    assert result["final_generic_turn_count"] == 0
    assert page.goto_calls == [
        ("https://chatgpt.com/g/g-p-current-demo/c/chat-1", "domcontentloaded"),
        ("https://chatgpt.com/g/g-p-current-demo/c/chat-1", "domcontentloaded"),
    ]


def test_ensure_target_conversation_hydrated_accepts_after_second_reload(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class DummyPage:
        url = "https://chatgpt.com/g/g-p-current-demo/c/chat-1"

        def __init__(self) -> None:
            self.goto_calls: list[tuple[str, str]] = []
            self.waits: list[int] = []

        async def goto(self, url: str, *, wait_until: str):
            self.goto_calls.append((url, wait_until))
            self.url = url

        async def wait_for_timeout(self, ms: int):
            self.waits.append(ms)

    page = DummyPage()
    samples = [
        {"count": 0, "generic_turns": {"count": 0}, "last_text_length": 0},
        {"count": 0, "generic_turns": {"count": 0}, "last_text_length": 0},
        {"count": 1, "generic_turns": {"count": 1}, "last_text_length": 12},
    ]

    async def fake_turn_state(page, *, prompt=None):
        return samples.pop(0) if samples else {"count": 1, "generic_turns": {"count": 1}, "last_text_length": 12}

    async def fake_wait_rate_limit(page, *, label: str, timeout_ms: int | None = None):
        return False

    async def fake_has_chat_input(page):
        return False

    client._capture_user_turn_state = fake_turn_state
    client._wait_for_rate_limit_modal_to_clear = fake_wait_rate_limit
    client._has_chat_input = fake_has_chat_input

    import asyncio

    result = asyncio.run(
        client._ensure_target_conversation_hydrated(
            page,
            target_url="https://chatgpt.com/g/g-p-current-demo/c/chat-1",
            label="chat-home-after-login",
            timeout_ms=0,
            poll_interval_ms=1,
        )
    )

    assert result["status"] == "target_conversation_hydrated_after_reload"
    assert result["reload_performed"] is True
    assert result["reload_count"] == 2
    assert page.goto_calls == [
        ("https://chatgpt.com/g/g-p-current-demo/c/chat-1", "domcontentloaded"),
        ("https://chatgpt.com/g/g-p-current-demo/c/chat-1", "domcontentloaded"),
    ]



def test_navigation_does_not_force_same_conversation_reload_by_default(tmp_path: Path, monkeypatch) -> None:
    client = _make_client(tmp_path)
    current_url = "https://chatgpt.com/g/g-p-current-demo/c/chat-1"

    monkeypatch.delenv("CHATGPT_HYDRATION_MODE", raising=False)
    assert client._navigation_requires_refresh(
        label="chat-home-after-login",
        current_url=current_url,
        target_url=current_url,
    ) is False

    monkeypatch.setenv("CHATGPT_HYDRATION_MODE", "legacy")
    assert client._navigation_requires_refresh(
        label="chat-home-after-login",
        current_url=current_url,
        target_url=current_url,
    ) is True


def test_ensure_target_conversation_hydrated_reuses_warm_task_when_composer_ready(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class DummyPage:
        url = "https://chatgpt.com/g/g-p-current-demo/c/chat-1"

        async def wait_for_timeout(self, ms: int):
            raise AssertionError("warm task reuse should not wait for transcript hydration")

        async def goto(self, *args, **kwargs):
            raise AssertionError("warm task reuse should not reload the task")

    async def fake_has_chat_input(page):
        return True

    async def fail_turn_state(page, *, prompt=None):
        raise AssertionError("warm task reuse should not count historical conversation turns")

    client._has_chat_input = fake_has_chat_input
    client._capture_user_turn_state = fail_turn_state

    import asyncio

    result = asyncio.run(
        client._ensure_target_conversation_hydrated(
            DummyPage(),
            target_url="https://chatgpt.com/g/g-p-current-demo/c/chat-1",
            label="chat-home-after-login",
            navigation_evidence={"mode": "same_url_skip", "skipped": True},
        )
    )

    assert result["status"] == "target_conversation_hydrated_warm_task_reuse"
    assert result["hydration_mode"] == "warm_task_reuse"
    assert result["hydration_reuse_candidate"] is True
    assert result["hydration_reuse_used"] is True
    assert result["hydration_fallback_used"] is False
    assert result["hydration_conversation_surface_seconds"] == 0.0
    assert result["hydration_navigation_skipped"] is True


def test_ensure_target_conversation_hydrated_accepts_existing_turns(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class DummyPage:
        async def wait_for_timeout(self, ms: int):
            raise AssertionError("should not wait when already hydrated")

    page = DummyPage()

    async def fake_turn_state(page, *, prompt=None):
        return {"count": 1, "generic_turns": {"count": 2}, "last_text_length": 12}

    client._capture_user_turn_state = fake_turn_state

    import asyncio

    result = asyncio.run(
        client._ensure_target_conversation_hydrated(
            page,
            target_url="https://chatgpt.com/g/g-p-current-demo/c/chat-1",
            label="chat-home-after-login",
        )
    )

    assert result["status"] == "target_conversation_hydrated"
    assert result["reload_performed"] is False


def test_wait_for_submit_confirmation_accepts_stop_button_signal(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class DummyPage:
        async def wait_for_timeout(self, ms: int):
            raise AssertionError("should not wait after immediate confirmation")

    async def fake_state(page, *, before_assistant_count: int):
        return {
            "confirmed": True,
            "confirmed_by": ["stop_button"],
            "stop_button_visible": True,
            "conversation_url_visible": False,
            "assistant_turn_count": before_assistant_count,
            "assistant_turn_delta": 0,
            "current_url": "https://chatgpt.com/g/g-p-current-demo/project",
        }

    client._capture_submit_confirmation_state = fake_state

    import asyncio

    result = asyncio.run(client._wait_for_submit_confirmation(DummyPage(), before_assistant_count=2))

    assert result["status"] == "submit_confirmed"
    assert result["confirmed"] is True
    assert result["confirmed_by"] == ["stop_button"]
    assert result["attempt_count"] == 2
    assert result["confirmation_mode"] == "strict_causal_probe"
    assert result["fallback_used"] is True
    assert result["causal_confirmation_verified"] is True
    assert result["causal_confirmation_reason"] == "running_state"



def test_wait_for_submit_confirmation_rejects_url_only_fast_path_by_default(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class DummyPage:
        url = "https://chatgpt.com/g/g-p-current-demo/c/chat-1"

        async def wait_for_timeout(self, ms: int):
            return None

    async def url_only_state(page, *, before_assistant_count: int):
        return {
            "confirmed": True,
            "confirmed_by": ["url_conversation"],
            "stop_button_visible": False,
            "conversation_url_visible": True,
            "assistant_turn_count": before_assistant_count,
            "assistant_turn_delta": 0,
            "current_url": "https://chatgpt.com/g/g-p-current-demo/c/chat-1",
            "probe_seconds": 0.0,
            "historical_count_used": True,
        }

    async def no_user_echo(page, *, prompt=None):
        return {"request_id_found": False, "prompt_prefix_found": False, "generic_turns": {}}

    async def no_backend_echo(page, *, prompt=None):
        return {"visible": False, "status": "backend_task_message_echo_not_visible", "probe_seconds": 0.0}

    client._capture_submit_confirmation_state = url_only_state
    client._capture_backend_task_message_echo_state = no_backend_echo
    client._capture_user_turn_state = no_user_echo

    import asyncio

    result = asyncio.run(client._wait_for_submit_confirmation(
        DummyPage(),
        before_assistant_count=145,
        prompt="Return exactly this JSON object with STALE_GUARD_LIVE_OK_1234567890",
        timeout_ms=1,
        poll_interval_ms=1,
    ))

    assert result["status"] == "submit_confirmation_not_observed"
    assert result["confirmed"] is False
    assert result["confirmed_by"] == []
    assert result["causal_confirmation_required"] is True
    assert result["causal_confirmation_verified"] is False
    assert result["causal_confirmation_reason"] == "causal_signal_not_observed"
    assert result["url_only_confirmation_rejected"] is True


def test_wait_for_submit_confirmation_accepts_post_submit_user_turn_echo(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class DummyPage:
        url = "https://chatgpt.com/g/g-p-current-demo/c/chat-1"

        async def wait_for_timeout(self, ms: int):
            raise AssertionError("user-turn echo should confirm without waiting")

    async def url_only_state(page, *, before_assistant_count: int):
        return {
            "confirmed": True,
            "confirmed_by": ["url_conversation"],
            "stop_button_visible": False,
            "conversation_url_visible": True,
            "assistant_turn_count": before_assistant_count,
            "assistant_turn_delta": 0,
            "current_url": "https://chatgpt.com/g/g-p-current-demo/c/chat-1",
            "probe_seconds": 0.0,
            "historical_count_used": True,
        }

    async def user_echo(page, *, prompt=None):
        return {
            "request_id_found": False,
            "response_marker_found": True,
            "exact_marker_found": True,
            "exact_matched_marker": "STALE_GUARD_LIVE_OK_1234567890",
            "prompt_prefix_found": False,
            "generic_turns": {"request_id_found": False, "response_marker_found": False, "exact_marker_found": False},
        }

    async def no_backend_echo(page, *, prompt=None):
        return {"visible": False, "status": "backend_task_message_echo_not_visible", "probe_seconds": 0.0}

    client._capture_submit_confirmation_state = url_only_state
    client._capture_backend_task_message_echo_state = no_backend_echo
    client._capture_user_turn_state = user_echo

    import asyncio

    result = asyncio.run(client._wait_for_submit_confirmation(
        DummyPage(),
        before_assistant_count=145,
        prompt="Return exactly this JSON object with STALE_GUARD_LIVE_OK_1234567890",
    ))

    assert result["status"] == "submit_confirmed"
    assert result["confirmed"] is True
    assert result["confirmed_by"] == ["user_turn_echo"]
    assert result["causal_confirmation_required"] is True
    assert result["causal_confirmation_verified"] is True
    assert result["causal_confirmation_reason"] == "user_turn_echo"
    assert result["url_only_confirmation_rejected"] is True
    assert result["user_turn_echo_found"] is True



def test_wait_for_submit_confirmation_accepts_backend_task_message_echo(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class DummyPage:
        url = "https://chatgpt.com/g/g-p-current-demo/c/chat-1"

        async def wait_for_timeout(self, ms: int):
            raise AssertionError("backend task-message echo should confirm without DOM polling")

    async def url_only_state(page, *, before_assistant_count: int):
        return {
            "confirmed": True,
            "confirmed_by": ["url_conversation"],
            "stop_button_visible": False,
            "conversation_url_visible": True,
            "assistant_turn_count": before_assistant_count,
            "assistant_turn_delta": 0,
            "current_url": "https://chatgpt.com/g/g-p-current-demo/c/chat-1",
            "probe_seconds": 0.0,
            "historical_count_used": True,
        }

    async def fail_dom_echo(page, *, prompt=None):
        raise AssertionError("DOM user-turn echo should not be needed when backend confirms")

    async def fake_conversation_detail(page, *, conversation_id: str):
        assert conversation_id == "chat-1"
        return {
            "ok": True,
            "status": 200,
            "used_authorization": True,
            "payload": {
                "current_node": "user-node",
                "mapping": {
                    "root": {"id": "root", "parent": None, "message": None},
                    "user-node": {
                        "id": "user-node",
                        "parent": "root",
                        "message": {
                            "author": {"role": "user"},
                            "content": {"parts": ["Return exactly this JSON object with STALE_GUARD_LIVE_OK_1234567890"]},
                        },
                    },
                },
            },
        }

    client._capture_submit_confirmation_state = url_only_state
    client._capture_user_turn_state = fail_dom_echo
    client._fetch_conversation_detail = fake_conversation_detail

    import asyncio

    result = asyncio.run(client._wait_for_submit_confirmation(
        DummyPage(),
        before_assistant_count=145,
        prompt="Return exactly this JSON object with STALE_GUARD_LIVE_OK_1234567890",
    ))

    assert result["status"] == "submit_confirmed"
    assert result["confirmed"] is True
    assert result["confirmed_by"] == ["backend_task_message"]
    assert result["causal_confirmation_verified"] is True
    assert result["causal_confirmation_reason"] == "backend_task_message"
    assert result["backend_task_message_found"] is True
    assert result["backend_task_message_status"] == "backend_task_message_echo_visible"
    assert result["url_only_confirmation_rejected"] is True
    evidence = result["backend_task_message_evidence"]
    assert evidence["source"] == "backend_conversation_detail"
    assert evidence["matched_user_turn_id"] == "user-node"
    assert "response_marker" in evidence["matched_by"]



def test_backend_task_message_echo_rejects_prompt_short_prefix_without_exact_marker(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class DummyPage:
        url = "https://chatgpt.com/g/g-p-current-demo/c/chat-1"

    current_prompt = (
        "Return exactly this JSON object after reading these strict rules. "
        "Use one JSON object only, no markdown, no prose, no comments, and preserve all fields. "
        'The payload is: {"ok": true, "sentinel": "STALE_GUARD_LIVE_OK_2222222222", "finished": "finished"}.'
    )
    stale_prompt = current_prompt.replace("2222222222", "1111111111")

    async def fake_conversation_detail(page, *, conversation_id: str):
        return {
            "ok": True,
            "status": 200,
            "used_authorization": True,
            "payload": {
                "current_node": "user-node",
                "mapping": {
                    "root": {"id": "root", "parent": None, "message": None},
                    "user-node": {
                        "id": "user-node",
                        "parent": "root",
                        "message": {
                            "author": {"role": "user"},
                            "content": {"parts": [stale_prompt]},
                        },
                    },
                },
            },
        }

    client._fetch_conversation_detail = fake_conversation_detail

    import asyncio

    evidence = asyncio.run(client._capture_backend_task_message_echo_state(DummyPage(), prompt=current_prompt))

    assert evidence["visible"] is False
    assert evidence["status"] == "backend_stale_user_turn_prefix_match_rejected"
    assert evidence["backend_stale_user_turn_prefix_match_rejected"] is True
    assert evidence["marker_present_in_matched_user_text"] is False
    assert evidence["matched_marker"] is None
    assert "STALE_GUARD_LIVE_OK_1111111111" in evidence["stale_marker_values_detected"]


def test_wait_for_submit_confirmation_rejects_backend_prefix_match_after_prepare(tmp_path: Path, monkeypatch) -> None:
    client = _make_client(tmp_path)
    monkeypatch.setenv("CHATGPT_SUBMIT_NETWORK_TIMEOUT_MS", "1")

    class DummyPage:
        async def wait_for_timeout(self, ms: int):
            return None

    observer = {
        "enabled": True,
        "started_at_monotonic": 100.0,
        "events": [
            {
                "url": "https://chatgpt.com/backend-api/f/conversation/prepare",
                "method": "POST",
                "backend_like": True,
                "mutating": True,
                "prepare_request": True,
                "message_request_candidate": False,
                "marker_found": False,
                "post_data_length": 500,
                "captured_at_monotonic": 100.25,
            }
        ],
        "responses": [],
        "matched_request": None,
        "matched_response": None,
        "status": "submit_network_observer_started",
    }

    async def backend_echo_after_prepare(page, *, prompt, timeout_ms=None, poll_interval_ms=500):
        return {
            "visible": False,
            "status": "backend_stale_user_turn_prefix_match_rejected",
            "post_prepare_commit_window_used": True,
            "post_prepare_commit_found": False,
            "post_prepare_commit_status": "backend_stale_user_turn_prefix_match_rejected",
            "backend_stale_user_turn_prefix_match_rejected": True,
            "marker_present_in_matched_user_text": False,
            "matched_marker": None,
            "stale_marker_values_detected": ["STALE_GUARD_LIVE_OK_1111111111"],
        }

    async def prepare_only_network(page, observer):
        return {
            "visible": False,
            "status": "submit_prepare_without_message_commit",
            "prepare_request_observed": True,
            "prepare_request_count": 1,
            "prepare_only": True,
            "request_marker_found": False,
            "message_request_observed": False,
            "message_request_count": 0,
            "conduit_error_hint": "prepare_token_set_not_consumed",
            "probe_seconds": 0.001,
        }

    client._wait_for_submit_network_evidence = prepare_only_network
    client._wait_for_backend_task_message_echo_after_prepare = backend_echo_after_prepare

    import asyncio

    result = asyncio.run(client._wait_for_submit_confirmation(
        DummyPage(),
        before_assistant_count=145,
        prompt='Return exactly this JSON object with STALE_GUARD_LIVE_OK_2222222222',
        submit_network_observer=observer,
    ))

    assert result["status"] == "submit_confirmation_not_observed"
    assert result["confirmed"] is False
    assert result["confirmation_mode"] == "prepare_only_without_exact_marker_commit"
    assert result["causal_confirmation_reason"] == "backend_stale_user_turn_prefix_match_rejected"
    assert result["backend_stale_user_turn_prefix_match_rejected"] is True
    assert result["matched_marker"] is None

def test_wait_for_submit_confirmation_fast_fails_prepare_only_before_retry(tmp_path: Path, monkeypatch) -> None:
    client = _make_client(tmp_path)
    monkeypatch.setenv("CHATGPT_SUBMIT_NETWORK_TIMEOUT_MS", "500")
    monkeypatch.setenv("CHATGPT_SUBMIT_PREPARE_FAST_FAIL_TIMEOUT_MS", "1")

    class DummyPage:
        async def wait_for_timeout(self, ms: int):
            return None

    observer = {
        "enabled": True,
        "started_at_monotonic": 100.0,
        "markers_count": 1,
        "events": [
            {
                "url": "https://chatgpt.com/backend-api/f/conversation/prepare",
                "method": "POST",
                "backend_like": True,
                "mutating": True,
                "prepare_request": True,
                "message_request_candidate": False,
                "marker_found": False,
                "post_data_length": 500,
                "captured_at_monotonic": 100.05,
            }
        ],
        "all_events": [],
        "responses": [],
        "all_responses": [
            {
                "url": "https://chatgpt.com/backend-api/f/conversation/prepare",
                "status": 200,
                "prepare_request": True,
                "captured_at_monotonic": 100.1,
                "body_shape": {
                    "json_parse_ok": True,
                    "json_type": "dict",
                    "top_level_keys": ["status", "conduit_token"],
                    "all_keys_sample": ["status", "conduit_token"],
                    "status_value": "ok",
                    "has_error": False,
                    "conversation_id_present": False,
                    "message_id_present": False,
                    "finalization_token_present": True,
                    "conduit_token_present": True,
                    "conduit_token_sha256_12": "abc123abc123",
                    "conduit_token_sha256_12_values": ["abc123abc123"],
                    "conduit_token_count": 1,
                },
            }
        ],
        "matched_request": None,
        "matched_response": None,
        "status": "submit_network_observer_started",
    }
    observer["all_events"] = list(observer["events"])

    async def backend_echo_after_prepare(*args, **kwargs):
        raise AssertionError("raw Enter prepare-only fast-fail should not run the slow backend commit window")

    client._wait_for_backend_task_message_echo_after_prepare = backend_echo_after_prepare

    import asyncio

    result = asyncio.run(client._wait_for_submit_confirmation(
        DummyPage(),
        before_assistant_count=145,
        prompt="Return exactly this JSON object with STALE_GUARD_LIVE_OK_1234567890",
        submit_network_observer=observer,
        prepare_only_fast_fail=True,
    ))

    assert result["status"] == "submit_confirmation_not_observed"
    assert result["confirmed"] is False
    assert result["prepare_only_fast_fail_used"] is True
    assert result["prepare_only_fast_fail_timeout_ms"] == 250
    assert result["causal_confirmation_reason"] == "prepare_token_set_not_consumed"
    assert result["network_submit_request_status"] == "prepare_token_set_not_consumed"
    assert result["backend_task_message_status"] == "backend_commit_probe_skipped_due_to_prepare_fast_fail"
    assert result["attempts"][-1]["mode"] == "prepare_only_fast_fail"


def test_wait_for_submit_confirmation_accepts_network_submit_marker(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class DummyPage:
        async def wait_for_timeout(self, ms: int):
            raise AssertionError("network submit evidence should confirm without DOM/backend polling")

    observer = {
        "enabled": True,
        "markers_count": 1,
        "events": [],
        "responses": [],
        "matched_request": {
            "url": "https://chatgpt.com/backend-api/conversation",
            "method": "POST",
            "marker_found": True,
            "matched_by": ["response_marker"],
            "matched_marker": "STALE_GUARD_LIVE_OK_1234567890",
            "post_data_length": 128,
            "observed_after_click_seconds": 0.025,
        },
        "matched_response": {
            "url": "https://chatgpt.com/backend-api/conversation",
            "method": "POST",
            "status": 200,
            "observed_after_click_seconds": 0.05,
        },
        "status": "submit_network_observer_started",
    }

    async def fail_state(page, *, before_assistant_count: int):
        raise AssertionError("DOM/backend submit confirmation should not run after network evidence")

    client._capture_submit_confirmation_state = fail_state

    import asyncio

    result = asyncio.run(client._wait_for_submit_confirmation(
        DummyPage(),
        before_assistant_count=145,
        prompt="Return exactly this JSON object with STALE_GUARD_LIVE_OK_1234567890",
        submit_network_observer=observer,
    ))

    assert result["status"] == "submit_confirmed"
    assert result["confirmed"] is True
    assert result["confirmed_by"] == ["network_submit_request"]
    assert result["causal_confirmation_verified"] is True
    assert result["causal_confirmation_reason"] == "network_submit_request"
    assert result["network_submit_request_observed"] is True
    assert result["submit_network_evidence"]["request_marker_found"] is True


def test_wait_for_submit_confirmation_fails_fast_when_network_submit_missing(tmp_path: Path, monkeypatch) -> None:
    client = _make_client(tmp_path)
    monkeypatch.setenv("CHATGPT_SUBMIT_NETWORK_TIMEOUT_MS", "1")

    class DummyPage:
        async def wait_for_timeout(self, ms: int):
            return None

    observer = {
        "enabled": True,
        "markers_count": 1,
        "events": [],
        "responses": [],
        "matched_request": None,
        "matched_response": None,
        "status": "submit_network_observer_started",
    }

    async def fail_state(page, *, before_assistant_count: int):
        raise AssertionError("backend/DOM causality should not run when required network proof is missing")

    client._capture_submit_confirmation_state = fail_state

    import asyncio

    result = asyncio.run(client._wait_for_submit_confirmation(
        DummyPage(),
        before_assistant_count=145,
        prompt="Return exactly this JSON object with STALE_GUARD_LIVE_OK_1234567890",
        submit_network_observer=observer,
    ))

    assert result["status"] == "submit_confirmation_not_observed"
    assert result["confirmed"] is False
    assert result["causal_confirmation_verified"] is False
    assert result["causal_confirmation_reason"] == "network_submit_request_not_observed"
    assert result["network_submit_request_observed"] is False
    assert result["attempts"][0]["mode"] == "network_submit"


def test_wait_for_submit_confirmation_reports_prepare_without_backend_commit(tmp_path: Path, monkeypatch) -> None:
    client = _make_client(tmp_path)
    monkeypatch.setenv("CHATGPT_SUBMIT_NETWORK_TIMEOUT_MS", "1")

    class DummyPage:
        async def wait_for_timeout(self, ms: int):
            return None

    observer = {
        "enabled": True,
        "started_at_monotonic": 100.0,
        "markers_count": 1,
        "events": [
            {
                "url": "https://chatgpt.com/backend-api/f/conversation/prepare",
                "method": "POST",
                "backend_like": True,
                "mutating": True,
                "prepare_request": True,
                "message_request_candidate": False,
                "marker_found": False,
                "post_data_length": 500,
                "captured_at_monotonic": 100.25,
            }
        ],
        "responses": [],
        "matched_request": None,
        "matched_response": None,
        "status": "submit_network_observer_started",
    }

    import asyncio

    result = asyncio.run(client._wait_for_submit_confirmation(
        DummyPage(),
        before_assistant_count=145,
        prompt="Return exactly this JSON object with STALE_GUARD_LIVE_OK_1234567890",
        submit_network_observer=observer,
    ))

    assert result["status"] == "submit_confirmation_not_observed"
    assert result["confirmed"] is False
    assert result["causal_confirmation_verified"] is False
    assert result["causal_confirmation_reason"] == "submit_prepare_without_backend_commit"
    assert result["confirmation_mode"] == "submit_prepare_backend_commit_timeout"
    assert result["network_submit_request_status"] == "submit_prepare_without_message_commit"
    assert result["backend_task_message_found"] is False
    assert result["backend_task_message_status"] == "backend_commit_after_prepare_not_found"
    assert result["prepare_request_observed"] is True
    assert result["prepare_request_count"] == 1
    assert result["prepare_only"] is True
    assert result["message_request_observed"] is False
    assert result["message_request_count"] == 0
    assert result["submit_network_evidence"]["status"] == "submit_prepare_without_message_commit"
    assert result["submit_network_evidence"]["prepare_first_observed_after_click_seconds"] == 0.25


def test_backend_task_message_wait_retries_backend_detail_503_then_confirms(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    calls = {"count": 0}

    class DummyPage:
        async def wait_for_timeout(self, ms: int):
            return None

    async def backend_echo(page, *, prompt=None):
        calls["count"] += 1
        if calls["count"] == 1:
            return {
                "visible": False,
                "status": "backend_task_message_echo_backend_detail_temporarily_unavailable",
                "backend_detail_temporarily_unavailable": True,
                "backend_detail_http_status": 503,
                "http_status": 503,
            }
        return {
            "visible": True,
            "status": "backend_task_message_echo_visible",
            "backend_detail_temporarily_unavailable": False,
            "backend_detail_http_status": 200,
            "http_status": 200,
            "matched_user_turn_id": "user-node-1",
            "matched_user_turn_index": 7,
            "matched_marker": "STALE_GUARD_LIVE_OK_1234567890",
            "marker_present_in_matched_user_text": True,
        }

    client._capture_backend_task_message_echo_state = backend_echo

    import asyncio

    result = asyncio.run(client._wait_for_backend_task_message_echo_after_prepare(
        DummyPage(),
        prompt="Return exactly this JSON object with STALE_GUARD_LIVE_OK_1234567890",
        timeout_ms=50,
        poll_interval_ms=1,
    ))

    assert result["post_prepare_commit_found"] is True
    assert result["post_prepare_commit_status"] == "backend_commit_after_prepare_found"
    assert result["backend_detail_http_statuses"] == [503, 200]
    assert result["backend_detail_transient_error_count"] == 1
    assert result["backend_detail_retry_count"] == 1
    assert result["matched_user_turn_id"] == "user-node-1"


def test_wait_for_submit_confirmation_classifies_backend_detail_503_after_prepare(tmp_path: Path, monkeypatch) -> None:
    client = _make_client(tmp_path)
    monkeypatch.setenv("CHATGPT_SUBMIT_NETWORK_TIMEOUT_MS", "1")

    class DummyPage:
        async def wait_for_timeout(self, ms: int):
            return None

    observer = {
        "enabled": True,
        "started_at_monotonic": 100.0,
        "markers_count": 1,
        "events": [
            {
                "url": "https://chatgpt.com/backend-api/f/conversation/prepare",
                "method": "POST",
                "backend_like": True,
                "mutating": True,
                "prepare_request": True,
                "message_request_candidate": False,
                "marker_found": False,
                "post_data_length": 500,
                "captured_at_monotonic": 100.25,
            }
        ],
        "responses": [],
        "matched_request": None,
        "matched_response": None,
        "status": "submit_network_observer_started",
    }

    async def backend_echo_after_prepare(page, *, prompt, timeout_ms=None, poll_interval_ms=500):
        return {
            "visible": False,
            "status": "backend_task_message_echo_backend_detail_temporarily_unavailable",
            "post_prepare_commit_window_used": True,
            "post_prepare_commit_found": False,
            "post_prepare_commit_status": "backend_detail_temporarily_unavailable",
            "post_prepare_commit_seconds": 0.321,
            "post_prepare_commit_attempt_count": 2,
            "backend_detail_http_status": 503,
            "backend_detail_http_statuses": [503, 503],
            "backend_detail_transient_error_count": 2,
            "backend_detail_retry_count": 1,
            "backend_detail_temporarily_unavailable": True,
        }

    client._wait_for_backend_task_message_echo_after_prepare = backend_echo_after_prepare

    import asyncio

    result = asyncio.run(client._wait_for_submit_confirmation(
        DummyPage(),
        before_assistant_count=145,
        prompt="Return exactly this JSON object with STALE_GUARD_LIVE_OK_1234567890",
        submit_network_observer=observer,
    ))

    assert result["status"] == "submit_confirmation_not_observed"
    assert result["confirmed"] is False
    assert result["confirmation_mode"] == "submit_backend_detail_temporarily_unavailable_timeout"
    assert result["causal_confirmation_reason"] == "backend_detail_temporarily_unavailable"
    assert result["backend_task_message_status"] == "backend_detail_temporarily_unavailable"
    assert result["backend_detail_http_statuses"] == [503, 503]
    assert result["backend_detail_transient_error_count"] == 2
    assert result["attempts"][-1]["backend_detail_temporarily_unavailable"] is True


def test_wait_for_submit_confirmation_accepts_backend_commit_after_prepare(tmp_path: Path, monkeypatch) -> None:
    client = _make_client(tmp_path)
    monkeypatch.setenv("CHATGPT_SUBMIT_NETWORK_TIMEOUT_MS", "1")

    class DummyPage:
        async def wait_for_timeout(self, ms: int):
            return None

    observer = {
        "enabled": True,
        "started_at_monotonic": 100.0,
        "markers_count": 1,
        "events": [
            {
                "url": "https://chatgpt.com/backend-api/f/conversation/prepare",
                "method": "POST",
                "backend_like": True,
                "mutating": True,
                "prepare_request": True,
                "message_request_candidate": False,
                "marker_found": False,
                "post_data_length": 500,
                "captured_at_monotonic": 100.25,
            }
        ],
        "responses": [],
        "matched_request": None,
        "matched_response": None,
        "status": "submit_network_observer_started",
    }

    async def backend_echo_after_prepare(page, *, prompt, timeout_ms=None, poll_interval_ms=500):
        return {
            "visible": True,
            "status": "backend_task_message_echo_visible",
            "post_prepare_commit_window_used": True,
            "post_prepare_commit_found": True,
            "post_prepare_commit_status": "backend_commit_after_prepare_found",
            "post_prepare_commit_seconds": 0.123,
            "post_prepare_commit_attempt_count": 1,
            "matched_marker": "STALE_GUARD_LIVE_OK_1234567890",
            "marker_present_in_matched_user_text": True,
        }

    client._wait_for_backend_task_message_echo_after_prepare = backend_echo_after_prepare

    import asyncio

    result = asyncio.run(client._wait_for_submit_confirmation(
        DummyPage(),
        before_assistant_count=145,
        prompt="Return exactly this JSON object with STALE_GUARD_LIVE_OK_1234567890",
        submit_network_observer=observer,
    ))

    assert result["status"] == "submit_confirmed"
    assert result["confirmed"] is True
    assert result["confirmed_by"] == ["backend_task_message"]
    assert result["causal_confirmation_verified"] is True
    assert result["causal_confirmation_reason"] == "backend_commit_after_prepare"
    assert result["backend_task_message_found"] is True
    assert result["backend_task_message_status"] == "backend_commit_after_prepare_found"
    assert result["attempts"][-1]["mode"] == "backend_commit_after_prepare"

def test_submit_prompt_button_path_skips_slow_user_turn_dom_wait_after_running_confirmation(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class DummyButton:
        async def count(self):
            return 1

        async def is_visible(self, timeout=None):
            return True

        async def is_enabled(self, timeout=None):
            return True

        async def click(self):
            return None

    class DummyLocator:
        @property
        def first(self):
            return DummyButton()

    class DummyPage:
        def locator(self, selector):
            return DummyLocator()

        async def wait_for_timeout(self, ms: int):
            raise AssertionError("button path should not wait after first enabled selector")

    async def fake_composer_state(page, *, prompt=None):
        return {
            "contains_prompt": True,
            "text_length": 0,
            "submit_button": {"send_ready": True},
        }

    async def fake_user_turn_state(page, *, prompt=None):
        return {"count": 0, "generic_turns": {"count": 0}, "last_text_length": 0}

    async def fake_count_assistant(page):
        return 0

    async def fake_confirmation(page, *, before_assistant_count, before_user_turn_state=None, prompt=None, timeout_ms=3000, poll_interval_ms=250, submit_network_observer=None):
        return {
            "status": "submit_confirmed",
            "confirmed": True,
            "confirmed_by": ["stop_button"],
            "duration_seconds": 0.05,
            "stop_button_visible": True,
            "assistant_turn_delta": 0,
        }

    async def fail_user_turn_dom(*args, **kwargs):
        raise AssertionError("_submit_prompt must not wait for slow user-turn DOM after submit confirmation")

    async def fail_post_submit_snapshot(*args, **kwargs):
        raise AssertionError("successful button path must skip post-submit composer snapshots")

    client._capture_composer_state = fake_composer_state
    client._capture_user_turn_state = fake_user_turn_state
    client._count_assistant_turns = fake_count_assistant
    client._wait_for_submit_confirmation = fake_confirmation
    client._wait_for_user_turn_dom_evidence = fail_user_turn_dom
    client._capture_post_submit_composer_state = fail_post_submit_snapshot

    import asyncio

    result = asyncio.run(client._submit_prompt(DummyPage(), prompt="hello"))

    assert result["submit_method"] == "button"
    assert result["submit_confirmed"] is True
    assert result["submit_confirmed_by"] == ["stop_button"]
    assert result["dom_user_turn_evidence"]["status"] == "user_turn_dom_evidence_skipped"
    assert result["after_submit_composer_snapshot_seconds"] == 0.0
    assert result["after_submit_snapshot_mode"] == "skipped_success_fast_path"
    assert result["after_submit_snapshot_skipped_reason"] == "submit_confirmed_without_deep_debug"
    assert result["after_composer"]["skipped"] is True
    assert "submit_dispatch_to_confirmation_seconds" in result
    assert "submit_accounted_seconds" in result
    assert "submit_unaccounted_seconds" in result
    assert abs(result["submit_unaccounted_seconds"]) < 0.1
    assert result["submit_wait_seconds"] >= result["submit_confirmation_seconds"]


def test_extract_last_text_from_selector_avoids_full_historical_evaluate_all(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class DummyItem:
        def __init__(self, index: int) -> None:
            self.index = index

        async def inner_text(self, timeout=None):
            return "LATEST" if self.index == 499 else "OLD"

        async def text_content(self, timeout=None):
            return ""

    class DummyLocator:
        async def count(self):
            return 500

        def nth(self, index: int):
            return DummyItem(index)

        async def evaluate_all(self, script):
            raise AssertionError("long historical evaluate_all must not run")

    class DummyPage:
        def locator(self, selector):
            return DummyLocator()

    import asyncio

    count, text = asyncio.run(client._extract_last_text_from_selector(DummyPage(), "[data-message-author-role='assistant']"))

    assert count == 500
    assert text == "LATEST"


def test_try_extract_json_payload_prefers_latest_assistant_turn_scope(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class DummyJsonItem:
        async def inner_text(self, timeout=None):
            return '{"ok": true, "sentinel": "SCOPED_JSON_OK"}'

        async def text_content(self, timeout=None):
            return ""

        async def is_visible(self, timeout=None):
            return True

    class ScopedJsonLocator:
        @property
        def last(self):
            return DummyJsonItem()

        async def count(self):
            return 1

    class DummyAssistantTurn:
        def locator(self, selector):
            return ScopedJsonLocator()

        async def inner_text(self, timeout=None):
            return '{"ok": true, "sentinel": "TURN_TEXT_OK"}'

        async def text_content(self, timeout=None):
            return ""

        async def is_visible(self, timeout=None):
            return True

    class GlobalLocator:
        async def count(self):
            raise AssertionError("global historical JSON selectors should not be used before scoped latest turn")

    class DummyPage:
        def locator(self, selector):
            return GlobalLocator()

    async def fake_last_assistant(page):
        return DummyAssistantTurn(), "section[data-turn='assistant']"

    client._get_last_assistant_turn_locator = fake_last_assistant

    import asyncio

    payload, selector, text_length, probes = asyncio.run(client._try_extract_json_payload(DummyPage()))

    assert payload == {"ok": True, "sentinel": "SCOPED_JSON_OK"}
    assert selector == "section[data-turn='assistant'] >> #code-block-viewer .cm-content"
    assert text_length > 0
    assert probes[0]["scoped_latest_turn"] is True



def test_try_extract_json_payload_with_freshness_context_ignores_pre_submit_turns(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class DummyJsonItem:
        def __init__(self, text: str) -> None:
            self.text = text

        async def inner_text(self, timeout=None):
            return self.text

        async def text_content(self, timeout=None):
            return ""

        async def is_visible(self, timeout=None):
            return True

    class ScopedJsonLocator:
        def __init__(self, text: str) -> None:
            self.text = text

        @property
        def last(self):
            return DummyJsonItem(self.text)

        async def count(self):
            return 1

    class AssistantTurn:
        def __init__(self, text: str) -> None:
            self.text = text

        def locator(self, selector):
            return ScopedJsonLocator(self.text)

        async def inner_text(self, timeout=None):
            return self.text

        async def text_content(self, timeout=None):
            return ""

        async def is_visible(self, timeout=None):
            return True

    class AssistantLocator:
        def __init__(self) -> None:
            self.turns = [
                AssistantTurn('{"ok": true, "sentinel": "OLD_PRE_SUBMIT"}'),
                AssistantTurn('{"ok": true, "sentinel": "NEW_POST_SUBMIT"}'),
            ]

        async def count(self):
            return len(self.turns)

        def nth(self, index: int):
            return self.turns[index]

        @property
        def last(self):
            return self.turns[-1]

    class EmptyLocator:
        async def count(self):
            return 0

        def nth(self, index: int):
            raise AssertionError("empty selector should not be indexed")

    class DummyPage:
        def locator(self, selector):
            if selector == 'section[data-turn="assistant"]':
                return AssistantLocator()
            return EmptyLocator()

    context = {
        "assistant_selector": 'section[data-turn="assistant"]',
        "assistant_count": 1,
        "assistant_text": '{"ok": true, "sentinel": "OLD_PRE_SUBMIT"}',
        "assistant_turn_baseline_counts": {'section[data-turn="assistant"]': 1},
        "pre_submit_payload_hashes": [client._stable_payload_hash({"ok": True, "sentinel": "OLD_PRE_SUBMIT"})],
    }

    import asyncio

    payload, selector, text_length, probes = asyncio.run(
        client._try_extract_json_payload(DummyPage(), response_context=context)
    )

    assert payload == {"ok": True, "sentinel": "NEW_POST_SUBMIT"}
    assert selector == 'section[data-turn="assistant"]:nth(1) >> #code-block-viewer .cm-content'
    assert text_length > 0
    assert all(probe.get("post_submit_only") for probe in probes)
    binding = context["last_response_payload_binding"]
    assert binding["bound_to_post_submit_turn"] is True
    assert binding["turn_index"] == 1
    assert binding["baseline_turn_index"] == 1
    assert binding["payload_seen_before_submit"] is False


def test_capture_conversation_dom_weight_light_mode_skips_historical_code_blocks(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class DummyLocator:
        async def count(self):
            raise AssertionError("light mode must not use broad locator counts")

    class DummyPage:
        def __init__(self) -> None:
            self.evaluated: list[str] = []

        async def evaluate(self, script, selector):
            self.evaluated.append(selector)
            values = {
                '[data-message-author-role="assistant"]': 145,
                '[data-message-author-role="user"]': 109,
                '[data-testid*="conversation-turn"]': 254,
            }
            return values.get(selector, 0)

        def locator(self, selector):
            return DummyLocator()

    import asyncio

    result = asyncio.run(client._capture_conversation_dom_weight(DummyPage()))

    assert result["diagnostic_mode"] == "light"
    assert result["capture_mode"] == "light"
    assert result["capture_capped"] is True
    assert result["assistant_turn_count"] == 145
    assert result["user_turn_count"] == 109
    assert result["generic_turn_count"] == 254
    assert result["code_block_count"] is None
    assert result["code_block_count_mode"] == "skipped_light"
    assert result["historical_scan_used"] is False
    assert result["large_conversation_dom_detected"] is True


def test_capture_conversation_dom_weight_deep_mode_allows_exact_counts(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    calls: list[tuple[str, ...]] = []

    async def fake_count(page, selectors):
        calls.append(tuple(selectors))
        if selectors == ASSISTANT_MESSAGE_SELECTORS:
            return 12, selectors[0]
        if selectors == USER_MESSAGE_SELECTORS:
            return 8, selectors[0]
        if selectors == GENERIC_CONVERSATION_TURN_SELECTORS:
            return 20, selectors[0]
        if selectors == JSON_BLOCK_SELECTORS:
            return 222, selectors[0]
        return 0, None

    from promptbranch_browser_auth.client import (
        ASSISTANT_MESSAGE_SELECTORS,
        GENERIC_CONVERSATION_TURN_SELECTORS,
        JSON_BLOCK_SELECTORS,
        USER_MESSAGE_SELECTORS,
    )

    client._count_first_working_selector = fake_count

    import asyncio

    result = asyncio.run(client._capture_conversation_dom_weight(object(), mode="deep"))

    assert result["diagnostic_mode"] == "deep"
    assert result["capture_capped"] is False
    assert result["code_block_count"] == 222
    assert result["code_block_count_mode"] == "exact"
    assert result["historical_scan_used"] is True
    assert len(calls) == 4


def test_try_extract_json_payload_uses_latest_turn_text_before_historical_json_fallback(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class EmptyScopedJsonLocator:
        async def count(self):
            return 0

    class DummyAssistantTurn:
        def locator(self, selector):
            return EmptyScopedJsonLocator()

        async def inner_text(self, timeout=None):
            return '{"ok": true, "sentinel": "LATEST_TEXT_OK"}'

        async def text_content(self, timeout=None):
            return ""

        async def is_visible(self, timeout=None):
            return True

    class GlobalLocator:
        async def count(self):
            raise AssertionError("historical JSON fallback must not run when latest-turn text parses")

    class DummyPage:
        def locator(self, selector):
            return GlobalLocator()

    async def fake_last_assistant(page):
        return DummyAssistantTurn(), 'section[data-turn="assistant"]'

    client._get_last_assistant_turn_locator = fake_last_assistant
    context: dict[str, object] = {}

    import asyncio

    payload, selector, text_length, probes = asyncio.run(
        client._try_extract_json_payload(DummyPage(), response_context=context)
    )

    assert payload == {"ok": True, "sentinel": "LATEST_TEXT_OK"}
    assert selector == 'section[data-turn="assistant"]'
    assert context["last_response_extraction_mode"] == "latest_turn_text"
    assert context["last_response_historical_scan_used"] is False


def test_response_wait_timing_fields_accounts_post_stabilization_tail(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    fields = client._response_wait_timing_fields(
        {
            "response_wait_breakdown": {
                "response_wait_started_at_monotonic": 100.0,
                "response_first_probe_at_monotonic": 101.0,
                "response_first_parseable_json_at_monotonic": 104.0,
                "response_payload_stabilized_at_monotonic": 105.0,
                "response_wait_returned_at_monotonic": 119.5,
                "response_probe_attempt_count": 3,
            }
        },
        response_wait_started_at=100.0,
        response_wait_returned_at=119.5,
    )

    assert fields["response_wait_seconds"] == 5.0
    assert fields["response_post_stabilization_return_seconds"] == 14.5
    assert fields["response_first_parseable_json_at_monotonic"] == 104.0
    assert fields["response_probe_attempt_count"] == 3


def test_wait_and_get_json_fast_returns_latest_turn_json_without_completion_probe(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client.config.debug = True

    class DummyPage:
        url = "https://chatgpt.com/g/g-p-current-demo/c/test-conversation"

        async def wait_for_timeout(self, ms: int):
            raise AssertionError("latest-turn JSON fast return should not poll after parseable payload")

    async def fake_open(*args, **kwargs):
        return None

    async def fake_extract(page, *, response_context=None):
        if isinstance(response_context, dict):
            response_context["last_response_extraction_mode"] = "latest_turn_json"
        return (
            {"ok": True, "sentinel": "FAST_RETURN_OK"},
            'section[data-turn="assistant"] >> div[data-message-author-role="assistant"] pre',
            35,
            [
                {
                    "selector": 'section[data-turn="assistant"] >> div[data-message-author-role="assistant"] pre',
                    "count": 1,
                    "visible": True,
                    "text_length": 35,
                    "parsed": True,
                    "scoped_latest_turn": True,
                }
            ],
        )

    async def forbidden_submit_state(page):
        raise AssertionError("latest-turn JSON fast return should skip completion submit-state probe")

    async def forbidden_thinking_state(page):
        raise AssertionError("latest-turn JSON fast return should skip thinking-state probe")

    async def fake_safe_url(page):
        return page.url

    async def forbidden_save(*args, **kwargs):
        raise AssertionError("latest-turn JSON fast return should skip success-path debug artifact save")

    client._maybe_open_new_project_conversation = fake_open
    client._try_extract_json_payload = fake_extract
    client._probe_submit_button_state = forbidden_submit_state
    client._probe_thinking_state = forbidden_thinking_state
    client._safe_page_url = fake_safe_url
    client._save_response_diagnostics = forbidden_save

    import asyncio
    import time

    context = {"response_wait_started_at_monotonic": time.monotonic()}
    payload = asyncio.run(client._wait_and_get_json(DummyPage(), response_context=context))

    assert payload == {"ok": True, "sentinel": "FAST_RETURN_OK"}
    breakdown = context["response_wait_breakdown"]
    assert breakdown["response_probe_attempt_count"] == 1
    assert breakdown["response_parseable_probe_attempt_count"] == 1
    assert breakdown["response_json_fast_return_used"] is True
    assert breakdown["response_json_fast_return_reason"] == "latest_turn_json_parseable"
    assert breakdown["response_completion_signal_skipped"] is True
    assert breakdown["response_completion_signal_skipped_reason"] == "latest_turn_json_fast_return"
    assert breakdown["response_completion_signal_probe_seconds"] == 0.0
    assert breakdown["response_debug_artifact_saved"] is False
    assert breakdown["response_debug_artifact_seconds"] == 0.0
    assert breakdown["response_post_stabilization_return_seconds"] == 0.0



def test_wait_and_get_json_rejects_stale_latest_turn_before_fast_return(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client.config.debug = True

    old_payload = {"ok": True, "sentinel": "OLD_STALE"}
    new_payload = {"ok": True, "sentinel": "NEW_FRESH"}
    old_text = json.dumps(old_payload)
    new_text = json.dumps(new_payload)
    calls = {"extract": 0, "assistant_text": 0, "polls": 0}

    class DummyPage:
        url = "https://chatgpt.com/g/g-p-current-demo/c/test-conversation"

        async def wait_for_timeout(self, ms: int):
            calls["polls"] += 1
            return None

    async def fake_open(*args, **kwargs):
        return None

    async def fake_extract(page, *, response_context=None):
        calls["extract"] += 1
        if isinstance(response_context, dict):
            response_context["last_response_extraction_mode"] = "latest_turn_json"
        payload = old_payload if calls["extract"] == 1 else new_payload
        text = old_text if calls["extract"] == 1 else new_text
        if isinstance(response_context, dict):
            if calls["extract"] == 1:
                response_context["last_response_payload_binding"] = {
                    "bound_to_post_submit_turn": False,
                    "payload_hash": client._stable_payload_hash(payload),
                    "payload_seen_before_submit": True,
                    "pre_submit_payload_hashes_count": 1,
                    "turn_index": 0,
                    "baseline_turn_index": 1,
                    "current_turn_count": 1,
                }
            else:
                response_context["last_response_payload_binding"] = {
                    "bound_to_post_submit_turn": True,
                    "payload_hash": client._stable_payload_hash(payload),
                    "payload_seen_before_submit": False,
                    "pre_submit_payload_hashes_count": 1,
                    "turn_index": 1,
                    "baseline_turn_index": 1,
                    "current_turn_count": 2,
                }
        return (
            payload,
            'section[data-turn="assistant"] >> div[data-message-author-role="assistant"] pre',
            len(text),
            [
                {
                    "selector": 'section[data-turn="assistant"] >> div[data-message-author-role="assistant"] pre',
                    "count": 1,
                    "visible": True,
                    "text_length": len(text),
                    "parsed": True,
                    "scoped_latest_turn": True,
                    "post_submit_only": calls["extract"] > 1,
                }
            ],
        )

    async def fake_extract_last_text(page, selectors):
        calls["assistant_text"] += 1
        if calls["assistant_text"] == 1:
            return '[data-message-author-role="assistant"]', 1, old_text, []
        return '[data-message-author-role="assistant"]', 2, new_text, []

    async def fake_submit_state(page):
        return {
            "selector": 'button[aria-label="Start Voice"]',
            "idle_visible": True,
            "send_ready": True,
            "stop_visible": False,
            "aria_label": "Start Voice",
        }

    async def fake_thinking_state(page):
        return {"visible": False, "text": ""}

    async def fake_safe_url(page):
        return page.url

    async def fake_save(*args, **kwargs):
        return None

    client._maybe_open_new_project_conversation = fake_open
    client._try_extract_json_payload = fake_extract
    client._extract_last_text_from_selectors = fake_extract_last_text
    client._probe_submit_button_state = fake_submit_state
    client._probe_thinking_state = fake_thinking_state
    client._safe_page_url = fake_safe_url
    client._save_response_diagnostics = fake_save

    import asyncio
    import time

    context = {
        "response_wait_started_at_monotonic": time.monotonic(),
        "assistant_count": 1,
        "assistant_text": old_text,
    }
    payload = asyncio.run(client._wait_and_get_json(DummyPage(), response_context=context))

    assert payload == new_payload
    assert calls["extract"] == 2
    assert calls["polls"] >= 1
    breakdown = context["response_wait_breakdown"]
    assert breakdown["response_freshness_required"] is True
    assert breakdown["response_freshness_verified"] is True
    assert breakdown["response_freshness_reason"] == "post_submit_turn_payload"
    assert breakdown["response_stale_candidate_detected"] is True
    assert breakdown["response_payload_bound_to_post_submit_turn"] is True
    assert breakdown["response_payload_seen_before_submit"] is False
    assert breakdown["response_json_fast_return_used"] is True
    assert breakdown["response_completion_signal_skipped"] is True



def test_wait_and_get_json_requires_request_marker_even_when_turn_binding_claims_fresh(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client.config.debug = True

    token = "STALE_GUARD_LIVE_OK_1234567890"
    old_payload = {"ok": True, "sentinel": "SUBMIT_CONFIRMATION_FAST_PATH_OK", "finished": "finished"}
    fresh_payload = {"ok": True, "sentinel": token, "finished": "finished"}
    calls = {"extract": 0, "polls": 0}

    class DummyPage:
        url = "https://chatgpt.com/g/g-p-current-demo/c/test-conversation"

        async def wait_for_timeout(self, ms: int):
            calls["polls"] += 1
            return None

    async def fake_open(*args, **kwargs):
        return None

    async def fake_extract(page, *, response_context=None):
        calls["extract"] += 1
        payload = old_payload if calls["extract"] == 1 else fresh_payload
        if isinstance(response_context, dict):
            response_context["last_response_extraction_mode"] = "post_submit_turn_json"
            response_context["last_response_payload_binding"] = {
                "bound_to_post_submit_turn": True,
                "payload_hash": client._stable_payload_hash(payload),
                "payload_seen_before_submit": False,
                "pre_submit_payload_hashes_count": 0,
                "turn_index": 114,
                "baseline_turn_index": 0,
                "current_turn_count": 115,
            }
        return (
            payload,
            'section[data-turn="assistant"]:nth(114) >> div[data-message-author-role="assistant"] pre',
            len(json.dumps(payload)),
            [{"selector": "fake", "count": 1, "visible": True, "text_length": 42, "parsed": True}],
        )

    async def fake_submit_state(page):
        return {
            "selector": 'button[aria-label="Start Voice"]',
            "idle_visible": True,
            "send_ready": True,
            "stop_visible": False,
            "aria_label": "Start Voice",
        }

    async def fake_thinking_state(page):
        return {"visible": False, "text": ""}

    async def fake_safe_url(page):
        return page.url

    async def fake_save(*args, **kwargs):
        return None

    client._maybe_open_new_project_conversation = fake_open
    client._try_extract_json_payload = fake_extract
    client._probe_submit_button_state = fake_submit_state
    client._probe_thinking_state = fake_thinking_state
    client._safe_page_url = fake_safe_url
    client._save_response_diagnostics = fake_save

    import asyncio
    import time

    context = {
        "response_wait_started_at_monotonic": time.monotonic(),
        "assistant_count": 0,
        "assistant_text": "",
        "response_request_binding_required": True,
        "response_request_binding_mode": "prompt_marker",
        "response_request_markers": [token],
        "response_request_marker_count": 1,
        "response_request_nonce_key": "promptbranch_request_nonce",
    }
    payload = asyncio.run(client._wait_and_get_json(DummyPage(), response_context=context))

    assert payload == fresh_payload
    assert calls["extract"] == 2
    assert calls["polls"] >= 1
    breakdown = context["response_wait_breakdown"]
    assert breakdown["response_stale_candidate_detected"] is True
    assert breakdown["response_freshness_verified"] is True
    assert breakdown["response_freshness_reason"] == "request_marker_match"
    assert breakdown["response_request_binding_required"] is True
    assert breakdown["response_request_marker_verified"] is True
    assert breakdown["response_json_fast_return_used"] is True
    assert breakdown["response_json_fast_return_reason"] == "request_marker_match"


def test_strip_injected_response_nonce_before_returning_answer(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    context = {
        "response_request_nonce_injected": True,
        "response_request_nonce_key": "promptbranch_request_nonce",
        "response_wait_breakdown": {},
    }
    answer = {
        "ok": True,
        "sentinel": "NONCE_STRIP_OK",
        "promptbranch_request_nonce": "pb_req_abc123",
        "finished": "finished",
    }

    stripped = client._strip_response_request_nonce(answer, context)

    assert stripped == {"ok": True, "sentinel": "NONCE_STRIP_OK", "finished": "finished"}
    assert context["response_request_nonce_stripped_from_answer"] is True
    assert context["response_wait_breakdown"]["response_request_nonce_stripped_from_answer"] is True


def test_wait_and_get_json_deep_debug_keeps_completion_probe_and_diagnostics(tmp_path: Path, monkeypatch) -> None:
    client = _make_client(tmp_path)
    client.config.debug = True
    monkeypatch.setenv("CHATGPT_RESPONSE_DEBUG_ARTIFACTS", "1")

    class DummyPage:
        url = "https://chatgpt.com/g/g-p-current-demo/c/test-conversation"

        async def wait_for_timeout(self, ms: int):
            return None

    async def fake_open(*args, **kwargs):
        return None

    async def fake_extract(page, *, response_context=None):
        if isinstance(response_context, dict):
            response_context["last_response_extraction_mode"] = "latest_turn_json"
        return (
            {"ok": True, "sentinel": "TIMING_OK"},
            'section[data-turn="assistant"] >> div[data-message-author-role="assistant"] pre',
            35,
            [
                {
                    "selector": 'section[data-turn="assistant"] >> div[data-message-author-role="assistant"] pre',
                    "count": 1,
                    "visible": True,
                    "text_length": 35,
                    "parsed": True,
                    "scoped_latest_turn": True,
                }
            ],
        )

    async def fake_submit_state(page):
        return {
            "selector": 'button[aria-label="Start Voice"]',
            "idle_visible": True,
            "send_ready": False,
            "aria_label": "Start Voice",
            "data_testid": "",
            "stop_visible": False,
            "visible_enabled_count": 1,
        }

    async def fake_thinking_state(page):
        return {"visible": False, "text": ""}

    async def fake_safe_url(page):
        return page.url

    async def fake_save(*args, **kwargs):
        import asyncio

        await asyncio.sleep(0.02)

    client._maybe_open_new_project_conversation = fake_open
    client._try_extract_json_payload = fake_extract
    client._probe_submit_button_state = fake_submit_state
    client._probe_thinking_state = fake_thinking_state
    client._safe_page_url = fake_safe_url
    client._save_response_diagnostics = fake_save

    import asyncio
    import time

    context = {"response_wait_started_at_monotonic": time.monotonic()}
    payload = asyncio.run(client._wait_and_get_json(DummyPage(), response_context=context))

    assert payload == {"ok": True, "sentinel": "TIMING_OK"}
    breakdown = context["response_wait_breakdown"]
    assert breakdown["response_json_fast_return_used"] is False
    assert breakdown["response_json_fast_return_reason"] == "deep_debug_enabled"
    assert breakdown["response_completion_signal_skipped"] is False
    assert breakdown["response_completion_signal_probe_seconds"] is not None
    assert breakdown["response_debug_artifact_saved"] is True
    assert breakdown["response_debug_artifact_seconds"] >= 0.015
    assert breakdown["response_post_stabilization_return_seconds"] >= 0.015



def test_fill_chat_prompt_prefers_trusted_paste_over_locator_fill(tmp_path: Path, monkeypatch) -> None:
    client = _make_client(tmp_path)
    monkeypatch.delenv("CHATGPT_PROMPT_FILL_MODE", raising=False)

    class DummyKeyboard:
        def __init__(self):
            self.pressed = []
        async def press(self, key):
            self.pressed.append(key)
        async def insert_text(self, text):
            raise AssertionError("keyboard insert should not be used when trusted paste verifies")

    class DummyContext:
        async def grant_permissions(self, permissions, origin=None):
            return None

    class DummyPage:
        def __init__(self):
            self.keyboard = DummyKeyboard()
            self.context = DummyContext()
            self.clipboard_text = None
        async def evaluate(self, script, text):
            self.clipboard_text = text
        async def wait_for_timeout(self, ms):
            return None

    class DummyLocator:
        async def fill(self, text, timeout=None):
            raise AssertionError("locator.fill should not be used on trusted paste success")

    async def fake_click(locator, *, label, timeout_ms):
        return None

    async def fake_composer_state(page, *, prompt=None):
        return {
            "input_selector": "#prompt-textarea",
            "text_length": len(prompt or ""),
            "contains_prompt_prefix": True,
            "text_preview": (prompt or "")[:120],
        }

    client._click_locator_with_fallback = fake_click
    client._capture_composer_state = fake_composer_state

    import asyncio

    page = DummyPage()
    result = asyncio.run(client._fill_chat_prompt(page, DummyLocator(), prompt="hello STALE_GUARD_LIVE_OK_1"))

    assert result["method"] == "trusted_paste"
    assert result["trusted_input_used"] is True
    assert result["trusted_paste_used"] is True
    assert result["verification_passed"] is True
    assert page.clipboard_text == "hello STALE_GUARD_LIVE_OK_1"
    assert "Control+V" in page.keyboard.pressed




def test_submit_response_body_shape_reports_redacted_prepare_metadata(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    shape = client._submit_response_body_shape(
        json.dumps({
            "status": "ok",
            "conversation_id": "secret-conversation-id",
            "message_id": "secret-message-id",
            "finalization_token": "secret-token",
            "error": {"code": "prepare_warning"},
        }),
        url="https://chatgpt.com/backend-api/f/conversation/prepare",
        status=200,
    )

    assert shape["json_parse_ok"] is True
    assert shape["body_length"] > 0
    assert shape["body_sha256_12"]
    assert "conversation_id" in shape["top_level_keys"]
    assert shape["conversation_id_present"] is True
    assert shape["message_id_present"] is True
    assert shape["finalization_token_present"] is True
    assert shape["has_error"] is True
    assert shape["error_code"] == "prepare_warning"
    assert "secret-token" not in json.dumps(shape)


def test_submit_network_snapshot_reports_prepare_response_stream_and_console_diagnostics(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    prepare_event = {
        "url": "https://chatgpt.com/backend-api/f/conversation/prepare",
        "method": "POST",
        "backend_like": True,
        "mutating": True,
        "prepare_request": True,
        "message_request_candidate": False,
        "marker_found": False,
        "post_data_length": 500,
        "captured_at_monotonic": 100.25,
    }
    observer = {
        "enabled": True,
        "started_at_monotonic": 100.0,
        "markers_count": 1,
        "events": [prepare_event],
        "all_events": [prepare_event],
        "responses": [],
        "all_responses": [
            {
                "url": "https://chatgpt.com/backend-api/f/conversation/prepare",
                "status": 200,
                "prepare_request": True,
                "message_request_candidate": False,
                "captured_at_monotonic": 100.30,
                "body_shape": client._submit_response_body_shape('{"status":"ok","conversation_id":"c","message_id":"m"}', url="https://chatgpt.com/backend-api/f/conversation/prepare", status=200),
            },
            {
                "url": "https://chatgpt.com/backend-api/conversation/abc/stream_status",
                "status": 200,
                "prepare_request": False,
                "message_request_candidate": False,
                "captured_at_monotonic": 100.40,
                "body_shape": client._submit_response_body_shape('{"status":"idle"}', url="https://chatgpt.com/backend-api/conversation/abc/stream_status", status=200),
            },
            {
                "url": "https://chatgpt.com/backend-api/conversation/init",
                "status": 200,
                "prepare_request": False,
                "message_request_candidate": False,
                "captured_at_monotonic": 100.50,
                "body_shape": client._submit_response_body_shape('{"ready":true}', url="https://chatgpt.com/backend-api/conversation/init", status=200),
            },
        ],
        "console_events": [
            {"type": "warning", "text_preview": "post-prepare warning", "captured_at_monotonic": 100.60},
        ],
        "page_errors": [
            {"text_preview": "post-prepare page error", "captured_at_monotonic": 100.70},
        ],
        "matched_request": None,
        "matched_response": None,
        "status": "submit_network_observer_started",
    }

    snapshot = client._submit_network_evidence_snapshot(observer)

    assert snapshot["status"] == "submit_prepare_without_message_commit"
    assert snapshot["prepare_response_observed"] is True
    assert snapshot["prepare_response_statuses"] == [200]
    assert snapshot["prepare_response_keys"]
    assert snapshot["prepare_response_conversation_id_present"] is True
    assert snapshot["prepare_response_message_id_present"] is True
    assert snapshot["stream_status_summary"]["observed"] is True
    assert snapshot["conversation_init_summary"]["observed"] is True
    assert snapshot["post_prepare_console_error_count"] == 2
    assert snapshot["post_prepare_console_error_summaries"][0]["text_preview"] == "post-prepare warning"
    assert snapshot["post_prepare_page_error_summaries"][0]["text_preview"] == "post-prepare page error"

def test_submit_network_snapshot_reports_backend_write_diagnostics_without_marker(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class DummyRequest:
        url = "https://chatgpt.com/backend-api/f/conversation/prepare"
        method = "POST"
        post_data = "{\"conversation_id\":\"abc\"}"

    record = client._submit_network_request_record(DummyRequest(), prompt="Return sentinel STALE_GUARD_LIVE_OK_1234567890")
    observer = {
        "enabled": True,
        "markers_count": 1,
        "events": [record],
        "responses": [],
        "matched_request": None,
        "matched_response": None,
        "status": "submit_network_observer_started",
    }

    snapshot = client._submit_network_evidence_snapshot(observer)

    assert snapshot["visible"] is False
    assert snapshot["status"] == "submit_prepare_without_message_commit"
    assert snapshot["backend_write_event_count"] == 1
    assert snapshot["marker_event_count"] == 0
    assert snapshot["prepare_request_observed"] is True
    assert snapshot["prepare_request_count"] == 1
    assert snapshot["prepare_only"] is True
    assert snapshot["message_request_observed"] is False
    assert snapshot["message_request_count"] == 0
    assert snapshot["event_urls"] == ["https://chatgpt.com/backend-api/f/conversation/prepare"]
    assert snapshot["event_summaries"][0]["post_data_preview"] == "<redacted>"


def test_submit_network_snapshot_rejects_marker_bearing_prepare_as_submit_confirmation(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class DummyRequest:
        url = "https://chatgpt.com/backend-api/f/conversation/prepare"
        method = "POST"
        post_data = "{\"message\":\"Return sentinel STALE_GUARD_LIVE_OK_1234567890\"}"

    record = client._submit_network_request_record(DummyRequest(), prompt="Return sentinel STALE_GUARD_LIVE_OK_1234567890")
    assert record["marker_found"] is True
    assert record["prepare_request"] is True
    assert record["message_request_candidate"] is False

    observer = {
        "enabled": True,
        "started_at_monotonic": 100.0,
        "markers_count": 1,
        "events": [record],
        "all_events": [record],
        "responses": [],
        "all_responses": [],
        # Simulate a stale/buggy observer that previously promoted prepare as matched_request.
        "matched_request": record,
        "matched_response": None,
        "status": "submit_network_observer_started",
    }

    snapshot = client._submit_network_evidence_snapshot(observer)

    assert snapshot["visible"] is False
    assert snapshot["request_observed"] is False
    assert snapshot["request_marker_found"] is False
    assert snapshot["request_url"] is None
    assert snapshot["status"] == "submit_prepare_without_message_commit"
    assert snapshot["prepare_request_observed"] is True
    assert snapshot["message_request_observed"] is False
    assert snapshot["marker_event_count"] == 1


def test_submit_response_body_shape_reports_redacted_conduit_token_metadata(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    shape = client._submit_response_body_shape(
        json.dumps({"status": "ok", "conduit_token": "secret-conduit-token"}),
        url="https://chatgpt.com/backend-api/f/conversation/prepare",
        status=200,
    )

    assert shape["conduit_token_present"] is True
    assert shape["conduit_token_sha256_12"]
    assert "secret-conduit-token" not in json.dumps(shape)


def test_submit_network_snapshot_classifies_prepare_token_set_not_consumed(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    prepare_event = {
        "url": "https://chatgpt.com/backend-api/f/conversation/prepare",
        "method": "POST",
        "backend_like": True,
        "mutating": True,
        "prepare_request": True,
        "message_request_candidate": False,
        "marker_found": False,
        "post_data_length": 500,
        "captured_at_monotonic": 100.25,
    }
    prepare_shape = client._submit_response_body_shape(
        json.dumps({"status": "ok", "conduit_token": "secret-conduit-token"}),
        url="https://chatgpt.com/backend-api/f/conversation/prepare",
        status=200,
    )
    observer = {
        "enabled": True,
        "started_at_monotonic": 100.0,
        "markers_count": 1,
        "events": [prepare_event],
        "all_events": [prepare_event],
        "responses": [],
        "all_responses": [{
            "url": "https://chatgpt.com/backend-api/f/conversation/prepare",
            "status": 200,
            "prepare_request": True,
            "message_request_candidate": False,
            "captured_at_monotonic": 100.30,
            "body_shape": prepare_shape,
        }],
        "matched_request": None,
        "matched_response": None,
        "status": "submit_network_observer_started",
    }

    snapshot = client._submit_network_evidence_snapshot(observer)

    assert snapshot["status"] == "prepare_token_set_not_consumed"
    assert snapshot["prepare_conduit_token_present"] is True
    assert snapshot["prepare_conduit_token_sha256_12"] == prepare_shape["conduit_token_sha256_12"]
    assert snapshot["conduit_transport_observed"] is False
    assert snapshot["prepare_token_set_not_consumed"] is True
    assert snapshot["prepare_only_then_idle_without_commit"] is False
    assert snapshot["conduit_error_hint"] == "prepare_token_set_not_consumed"
    assert "secret-conduit-token" not in json.dumps(snapshot)


def test_submit_network_snapshot_classifies_conduit_transport_without_commit(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    token = "secret-conduit-token"
    token_hash = client._submit_conduit_token_sha256_12(token)
    prepare_event = {
        "url": "https://chatgpt.com/backend-api/f/conversation/prepare",
        "method": "POST",
        "backend_like": True,
        "mutating": True,
        "prepare_request": True,
        "message_request_candidate": False,
        "marker_found": False,
        "post_data_length": 500,
        "captured_at_monotonic": 100.25,
    }
    conduit_event = {
        "url": "https://chatgpt.com/backend-api/conduit/finalize",
        "method": "POST",
        "backend_like": True,
        "mutating": True,
        "prepare_request": False,
        "message_request_candidate": True,
        "marker_found": False,
        "post_data_length": 100,
        "captured_at_monotonic": 100.45,
        "_private_combined_text": f"token={token}",
    }
    observer = {
        "enabled": True,
        "started_at_monotonic": 100.0,
        "markers_count": 1,
        "events": [prepare_event, conduit_event],
        "all_events": [prepare_event, conduit_event],
        "responses": [],
        "all_responses": [],
        "websockets": [{
            "url": "wss://chatgpt.com/backend-api/conduit",
            "frames": [{
                "direction": "sent",
                "payload_length": len(token),
                "captured_at_monotonic": 100.50,
                "_private_payload_text": token,
            }],
            "frame_sent_count": 1,
            "frame_received_count": 0,
        }],
        "prepare_conduit_tokens_private": [token],
        "prepare_conduit_token_sha256_12": token_hash,
        "prepare_conduit_token_sha256_12_values": [token_hash],
        "prepare_conduit_token_present": True,
        "matched_request": None,
        "matched_response": None,
        "status": "submit_network_observer_started",
    }

    snapshot = client._submit_network_evidence_snapshot(observer)

    assert snapshot["status"] == "submit_conduit_transport_observed_without_commit"
    assert snapshot["conduit_transport_observed"] is True
    assert snapshot["conduit_token_seen_in_request"] is True
    assert snapshot["conduit_token_seen_in_websocket"] is True
    assert snapshot["conduit_transport_kind"] == "mixed"
    assert snapshot["conduit_websocket_frame_count"] == 1
    assert snapshot["conduit_error_hint"] == "submit_conduit_transport_observed_without_commit"
    assert snapshot["prepare_conduit_token_sha256_12"] == token_hash
    assert token not in json.dumps(snapshot)



def test_submit_response_body_shape_reports_all_redacted_conduit_token_metadata(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    shape = client._submit_response_body_shape(
        json.dumps({
            "status": "ok",
            "items": [
                {"conduit_token": "secret-conduit-token-one"},
                {"conduitToken": "secret-conduit-token-two"},
            ],
        }),
        url="https://chatgpt.com/backend-api/f/conversation/prepare",
        status=200,
    )

    assert shape["conduit_token_present"] is True
    assert shape["conduit_token_count"] == 2
    assert len(shape["conduit_token_sha256_12_values"]) == 2
    assert "secret-conduit-token-one" not in json.dumps(shape)
    assert "secret-conduit-token-two" not in json.dumps(shape)


def test_submit_network_request_record_captures_resource_type_and_initiator(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class DummyFrame:
        url = "https://chatgpt.com/g/example/c/abc"

    class DummyRequest:
        url = "https://chatgpt.com/backend-api/conversation/abc/stream_status"
        method = "GET"
        resource_type = "fetch"
        frame = DummyFrame()

        def post_data(self) -> str:
            return ""

        def is_navigation_request(self) -> bool:
            return False

    record = client._submit_network_request_record(DummyRequest(), prompt="Return sentinel STALE_GUARD_LIVE_OK_1234567890")

    assert record["resource_type"] == "fetch"
    assert record["navigation_request"] is False
    assert record["initiator"]["available"] is True
    assert record["initiator"]["source"] == "request.frame"
    assert record["initiator"]["url"] == "https://chatgpt.com/g/example/c/abc"


def test_submit_network_snapshot_tracks_all_prepare_conduit_tokens(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    token_one = "secret-conduit-token-one"
    token_two = "secret-conduit-token-two"
    prepare_event = {
        "url": "https://chatgpt.com/backend-api/f/conversation/prepare",
        "method": "POST",
        "backend_like": True,
        "mutating": True,
        "prepare_request": True,
        "message_request_candidate": False,
        "marker_found": False,
        "post_data_length": 500,
        "captured_at_monotonic": 100.25,
    }
    shape_one = client._submit_response_body_shape(
        json.dumps({"status": "ok", "conduit_token": token_one}),
        url="https://chatgpt.com/backend-api/f/conversation/prepare",
        status=200,
    )
    shape_two = client._submit_response_body_shape(
        json.dumps({"status": "ok", "conduit_token": token_two}),
        url="https://chatgpt.com/backend-api/f/conversation/prepare",
        status=200,
    )
    observer = {
        "enabled": True,
        "started_at_monotonic": 100.0,
        "markers_count": 1,
        "events": [prepare_event],
        "all_events": [prepare_event],
        "responses": [],
        "all_responses": [
            {
                "url": "https://chatgpt.com/backend-api/f/conversation/prepare",
                "status": 200,
                "prepare_request": True,
                "message_request_candidate": False,
                "captured_at_monotonic": 100.30,
                "body_shape": shape_one,
            },
            {
                "url": "https://chatgpt.com/backend-api/f/conversation/prepare",
                "status": 200,
                "prepare_request": True,
                "message_request_candidate": False,
                "captured_at_monotonic": 100.35,
                "body_shape": shape_two,
            },
        ],
        "matched_request": None,
        "matched_response": None,
        "status": "submit_network_observer_started",
    }

    snapshot = client._submit_network_evidence_snapshot(observer)

    assert snapshot["prepare_conduit_token_count"] == 2
    assert snapshot["prepare_conduit_token_active_policy"] == "all_tokens"
    assert snapshot["prepare_conduit_token_sha256_12"] == shape_one["conduit_token_sha256_12"]
    assert snapshot["prepare_conduit_token_latest_sha256_12"] == shape_two["conduit_token_sha256_12"]
    assert snapshot["prepare_conduit_token_sha256_12_values"] == [
        shape_one["conduit_token_sha256_12"],
        shape_two["conduit_token_sha256_12"],
    ]
    assert token_one not in json.dumps(snapshot)
    assert token_two not in json.dumps(snapshot)


def test_submit_network_snapshot_classifies_stream_started_without_user_message_commit(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    prepare_event = {
        "url": "https://chatgpt.com/backend-api/f/conversation/prepare",
        "method": "POST",
        "backend_like": True,
        "mutating": True,
        "prepare_request": True,
        "message_request_candidate": False,
        "marker_found": False,
        "post_data_length": 500,
        "captured_at_monotonic": 100.25,
    }
    stream_shape = client._submit_response_body_shape(
        json.dumps({"status": "IS_STREAMING"}),
        url="https://chatgpt.com/backend-api/conversation/abc/stream_status",
        status=200,
    )
    observer = {
        "enabled": True,
        "started_at_monotonic": 100.0,
        "markers_count": 1,
        "events": [prepare_event],
        "all_events": [prepare_event],
        "responses": [],
        "all_responses": [
            {
                "url": "https://chatgpt.com/backend-api/conversation/abc/stream_status",
                "status": 200,
                "prepare_request": False,
                "message_request_candidate": False,
                "captured_at_monotonic": 100.40,
                "body_shape": stream_shape,
            },
        ],
        "matched_request": None,
        "matched_response": None,
        "status": "submit_network_observer_started",
    }

    snapshot = client._submit_network_evidence_snapshot(observer)

    assert snapshot["status"] == "stream_started_without_user_message_commit"
    assert snapshot["conduit_error_hint"] == "stream_started_without_user_message_commit"
    assert snapshot["stream_started_without_user_message_commit"] is True
    assert snapshot["post_prepare_stream_status_streaming_observed"] is True
    assert snapshot["post_prepare_stream_observed"] is True


def test_submit_network_snapshot_classifies_prepare_only_then_idle_without_commit(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    prepare_event = {
        "url": "https://chatgpt.com/backend-api/f/conversation/prepare",
        "method": "POST",
        "backend_like": True,
        "mutating": True,
        "prepare_request": True,
        "message_request_candidate": False,
        "marker_found": False,
        "post_data_length": 500,
        "captured_at_monotonic": 100.25,
    }
    prepare_shape = client._submit_response_body_shape(
        json.dumps({"status": "ok", "conduit_token": "secret-conduit-token"}),
        url="https://chatgpt.com/backend-api/f/conversation/prepare",
        status=200,
    )
    stream_shape = client._submit_response_body_shape(
        json.dumps({"status": "COMPLETE"}),
        url="https://chatgpt.com/backend-api/conversation/abc/stream_status",
        status=200,
    )
    observer = {
        "enabled": True,
        "started_at_monotonic": 100.0,
        "markers_count": 1,
        "events": [prepare_event],
        "all_events": [prepare_event],
        "responses": [],
        "all_responses": [
            {
                "url": "https://chatgpt.com/backend-api/f/conversation/prepare",
                "status": 200,
                "prepare_request": True,
                "message_request_candidate": False,
                "captured_at_monotonic": 100.30,
                "body_shape": prepare_shape,
            },
            {
                "url": "https://chatgpt.com/backend-api/conversation/abc/stream_status",
                "status": 200,
                "prepare_request": False,
                "message_request_candidate": False,
                "captured_at_monotonic": 100.40,
                "body_shape": stream_shape,
            },
        ],
        "matched_request": None,
        "matched_response": None,
        "status": "submit_network_observer_started",
    }

    snapshot = client._submit_network_evidence_snapshot(observer)

    assert snapshot["status"] == "prepare_only_then_idle_without_commit"
    assert snapshot["conduit_error_hint"] == "prepare_only_then_idle_without_commit"
    assert snapshot["prepare_token_set_not_consumed"] is True
    assert snapshot["prepare_only_then_idle_without_commit"] is True
    assert snapshot["post_prepare_stream_status_complete_observed"] is True
    assert snapshot["post_prepare_stream_status_streaming_observed"] is False
    assert snapshot["conduit_transport_observed"] is False
    assert "secret-conduit-token" not in json.dumps(snapshot)


def test_post_prepare_ui_error_text_filter_ignores_composer_footer_noise(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    assert client._post_prepare_ui_error_text_is_strict(
        "Instant\nUse Voice\nCtrl\nShift\nV\nChatGPT can make mistakes. Check important info.",
        selector='[role="alert"]',
    ) is False
    assert client._post_prepare_ui_error_text_is_strict(
        "Something went wrong. Please try again.",
        selector='[role="alert"]',
    ) is True


def test_submit_variant_network_summary_reports_keyboard_prepare_only(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    confirmation = {
        "confirmed": False,
        "confirmation_mode": "submit_prepare_only_then_idle_without_commit_timeout",
        "causal_confirmation_reason": "prepare_only_then_idle_without_commit",
        "submit_network_evidence": {
            "status": "prepare_only_then_idle_without_commit",
            "prepare_request_observed": True,
            "prepare_request_count": 2,
            "prepare_only": True,
            "prepare_only_then_idle_without_commit": True,
            "prepare_token_set_not_consumed": True,
            "message_request_observed": False,
            "message_request_count": 0,
            "conduit_transport_observed": False,
            "conduit_error_hint": "prepare_only_then_idle_without_commit",
            "stream_status_values": ["COMPLETE"],
            "post_prepare_stream_status_values": ["COMPLETE"],
        },
    }

    summary = client._submit_variant_network_summary(confirmation, variant="keyboard_enter", dispatch_key="Enter")

    assert summary["variant"] == "keyboard_enter"
    assert summary["dispatch_key"] == "Enter"
    assert summary["confirmed"] is False
    assert summary["network_status"] == "prepare_only_then_idle_without_commit"
    assert summary["prepare_only_then_idle_without_commit"] is True
    assert summary["prepare_token_set_not_consumed"] is True

def test_keyboard_enter_primary_submit_enabled_defaults_on_and_has_escape_hatch(tmp_path: Path, monkeypatch) -> None:
    client = _make_client(tmp_path)

    monkeypatch.delenv("CHATGPT_KEYBOARD_ENTER_PRIMARY_SUBMIT", raising=False)
    assert client._keyboard_enter_primary_submit_enabled() is True

    monkeypatch.setenv("CHATGPT_KEYBOARD_ENTER_PRIMARY_SUBMIT", "0")
    assert client._keyboard_enter_primary_submit_enabled() is False

    monkeypatch.setenv("CHATGPT_KEYBOARD_ENTER_PRIMARY_SUBMIT", "button")
    assert client._keyboard_enter_primary_submit_enabled() is False

    monkeypatch.setenv("CHATGPT_KEYBOARD_ENTER_PRIMARY_SUBMIT", "1")
    assert client._keyboard_enter_primary_submit_enabled() is True

def test_submit_prompt_uses_keyboard_enter_as_primary_dispatch(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    observer = {"observer": "network"}

    class DummyKeyboard:
        def __init__(self) -> None:
            self.pressed: list[str] = []

        async def press(self, key: str):
            self.pressed.append(key)

    class DummyPage:
        def __init__(self) -> None:
            self.keyboard = DummyKeyboard()

        def locator(self, selector):
            raise AssertionError("keyboard-primary submit must not probe the button")

        async def wait_for_timeout(self, ms: int):
            raise AssertionError("keyboard-primary submit must not wait for button fallback")

    async def fake_composer_state(page, *, prompt=None):
        return {
            "contains_prompt_prefix": True,
            "text_length": len(prompt or ""),
            "submit_button": {"send_ready": True},
        }

    async def fake_count_assistant(page):
        return 0

    async def fake_confirmation(page, *, before_assistant_count, before_user_turn_state=None, prompt=None, timeout_ms=3000, poll_interval_ms=250, submit_network_observer=None):
        assert submit_network_observer is observer
        return {
            "status": "submit_confirmed",
            "confirmed": True,
            "confirmed_by": ["network_submit_request"],
            "confirmation_mode": "network_submit_request",
            "network_submit_request_observed": True,
            "network_submit_request_status": "submit_network_request_observed",
            "causal_confirmation_required": True,
            "causal_confirmation_verified": True,
            "causal_confirmation_reason": "network_submit_request",
            "duration_seconds": 0.05,
            "submit_network_evidence": {
                "status": "submit_network_request_observed",
                "request_marker_found": True,
                "message_request_observed": True,
                "message_request_count": 1,
                "prepare_request_observed": False,
                "prepare_only": False,
                "backend_write_event_count": 1,
                "marker_event_count": 1,
                "event_urls": ["https://chatgpt.com/backend-api/f/conversation"],
            },
            "backend_task_message_evidence": {
                "post_prepare_commit_found": False,
            },
        }

    async def fail_post_submit_snapshot(*args, **kwargs):
        raise AssertionError("successful keyboard-primary path should skip deep snapshot by default")

    page = DummyPage()
    client._capture_composer_state = fake_composer_state
    client._count_assistant_turns = fake_count_assistant
    client._wait_for_submit_confirmation = fake_confirmation
    client._capture_post_submit_composer_state = fail_post_submit_snapshot
    client._start_submit_network_observer = lambda page, prompt=None: observer
    client._stop_submit_network_observer = lambda page, observer: None

    import asyncio

    result = asyncio.run(client._submit_prompt(page, prompt="hello"))

    assert page.keyboard.pressed == ["Enter"]
    assert result["submit_method"] == "keyboard_enter"
    assert result["clicked"] is False
    assert result["enter_fallback_used"] is False
    assert result["submit_keyboard_enter_primary_used"] is True
    assert result["submit_keyboard_enter_submit_confirmed"] is True
    assert result["submit_keyboard_enter_fresh_answer_gate_required"] is True
    assert result["submit_confirmed"] is True
    assert result["submit_network_request_marker_found"] is True
    assert result["after_submit_snapshot_mode"] == "skipped_success_fast_path"



def test_submit_prompt_retries_keyboard_enter_after_prepare_only_without_commit(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    observer = {"observer": "network"}

    class DummyKeyboard:
        def __init__(self) -> None:
            self.pressed: list[str] = []

        async def press(self, key: str):
            self.pressed.append(key)

    class DummyPage:
        def __init__(self) -> None:
            self.keyboard = DummyKeyboard()

        def locator(self, selector):
            raise AssertionError("input probing is monkeypatched for this test")

        async def wait_for_timeout(self, ms: int):
            return None

    async def fake_composer_state(page, *, prompt=None):
        return {
            "contains_prompt_prefix": True,
            "text_length": len(prompt or ""),
            "submit_button": {"send_ready": True},
        }

    async def fake_count_assistant(page):
        return 0

    async def first_confirmation(page, *, before_assistant_count, before_user_turn_state=None, prompt=None, timeout_ms=3000, poll_interval_ms=250, submit_network_observer=None):
        return {
            "status": "submit_confirmation_not_observed",
            "confirmed": False,
            "confirmed_by": [],
            "confirmation_mode": "submit_prepare_only_then_idle_without_commit_timeout",
            "network_submit_request_observed": False,
            "network_submit_request_status": "prepare_only_then_idle_without_commit",
            "causal_confirmation_required": True,
            "causal_confirmation_verified": False,
            "causal_confirmation_reason": "prepare_only_then_idle_without_commit",
            "duration_seconds": 0.1,
            "submit_network_evidence": {
                "status": "prepare_only_then_idle_without_commit",
                "prepare_request_observed": True,
                "prepare_request_count": 3,
                "prepare_only": True,
                "prepare_only_then_idle_without_commit": True,
                "prepare_token_set_not_consumed": True,
                "message_request_observed": False,
                "message_request_count": 0,
            },
            "backend_task_message_evidence": {
                "post_prepare_commit_found": False,
                "post_prepare_commit_status": "backend_commit_after_prepare_not_found",
            },
        }

    async def retry_variant(page, *, prompt, before_assistant_count, before_user_turn_state, variant, dispatch_key):
        return {
            "variant": variant,
            "dispatch_key": dispatch_key,
            "confirmed": True,
            "network_status": "submit_network_request_observed",
            "confirmation": {
                "status": "submit_confirmed",
                "confirmed": True,
                "confirmed_by": ["backend_task_message"],
                "confirmation_mode": "backend_commit_after_prepare",
                "backend_task_message_found": True,
                "backend_task_message_status": "backend_commit_after_prepare_found",
                "causal_confirmation_required": True,
                "causal_confirmation_verified": True,
                "causal_confirmation_reason": "backend_commit_after_prepare",
                "network_submit_request_observed": False,
                "network_submit_request_status": "submit_network_request_observed",
                "submit_network_evidence": {
                    "status": "submit_network_request_observed",
                    "request_marker_found": True,
                    "message_request_observed": True,
                    "message_request_count": 1,
                },
                "backend_task_message_evidence": {
                    "post_prepare_commit_found": True,
                    "post_prepare_commit_status": "backend_commit_after_prepare_found",
                },
            },
        }

    page = DummyPage()
    client._capture_composer_state = fake_composer_state
    client._count_assistant_turns = fake_count_assistant
    client._wait_for_submit_confirmation = first_confirmation
    client._run_keyboard_submit_variant = retry_variant
    client._find_visible_chat_input_for_submit_variant = lambda page: _async_tuple((None, None))
    client._start_submit_network_observer = lambda page, prompt=None: observer
    client._stop_submit_network_observer = lambda page, observer: None

    import asyncio

    result = asyncio.run(client._submit_prompt(page, prompt="hello"))

    assert page.keyboard.pressed == ["Enter"]
    assert result["submit_method"] == "keyboard_enter"
    assert result["submit_keyboard_enter_retry_used"] is True
    assert result["submit_keyboard_enter_retry_result"]["variant"] == "keyboard_enter_refill_retry"
    assert result["submit_confirmed"] is True
    assert result["submit_confirmed_by"] == ["backend_task_message"]
    assert result["submit_keyboard_enter_backend_commit_confirmed"] is True


def test_backend_answer_wait_disabled_by_default_and_legacy_dom_first_mode(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    assert client._ask_retrieval_mode() == "legacy_dom_first"
    assert client._backend_answer_wait_enabled() is False

    context: dict[str, object] = {}
    client._configure_backend_answer_wait_context(
        context,
        submit_evidence={
            "submit_confirmed": True,
            "backend_task_message_evidence": {
                "conversation_id": "conv-123",
                "matched_user_turn_id": "user-node-1",
                "matched_user_turn_index": 1,
            },
        },
    )

    assert context["ask_retrieval_mode"] == "legacy_dom_first"
    assert context["backend_answer_wait_enabled"] is False


def test_configure_backend_answer_wait_context_keys_to_matched_user_turn(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CHATGPT_BACKEND_FIRST_ANSWER_WAIT", "1")
    client = _make_client(tmp_path)
    context: dict[str, object] = {}
    submit_evidence = {
        "submit_confirmed": True,
        "backend_task_message_evidence": {
            "conversation_id": "conv-123",
            "matched_user_turn_id": "user-node-1",
            "matched_user_turn_index": 42,
        },
    }

    client._configure_backend_answer_wait_context(context, submit_evidence=submit_evidence)

    assert context["backend_answer_wait_enabled"] is True
    assert context["backend_answer_wait_keyed_to_user_commit"] is True
    assert context["backend_answer_conversation_id"] == "conv-123"
    assert context["backend_answer_user_turn_id"] == "user-node-1"
    assert context["backend_answer_user_turn_index"] == 42
    assert context["backend_answer_wait_timeout_ms"] == 120_000


def test_try_extract_json_payload_uses_backend_assistant_after_committed_user_turn_first(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CHATGPT_BACKEND_FIRST_ANSWER_WAIT", "1")
    client = _make_client(tmp_path)
    token = "STALE_GUARD_LIVE_OK_1234567890"
    payload = {"ok": True, "sentinel": token, "finished": "finished"}

    class DummyPage:
        def locator(self, selector):
            raise AssertionError("backend-first extraction must not touch DOM before backend answer probe succeeds")

    async def fake_fetch(page, *, conversation_id):
        assert conversation_id == "conv-123"
        return {
            "ok": True,
            "status": 200,
            "used_authorization": True,
            "payload": {
                "current_node": "assistant-node-1",
                "mapping": {
                    "root": {"parent": None, "message": None},
                    "user-node-1": {
                        "parent": "root",
                        "message": {
                            "author": {"role": "user"},
                            "content": {"parts": ["Return JSON with sentinel"]},
                        },
                    },
                    "assistant-node-1": {
                        "parent": "user-node-1",
                        "message": {
                            "author": {"role": "assistant"},
                            "content": {"parts": [json.dumps(payload)]},
                        },
                    },
                },
            },
        }

    client._fetch_conversation_detail = fake_fetch
    context = {
        "assistant_count": 115,
        "assistant_text": "old stale answer",
        "assistant_turn_baseline_counts": {'section[data-turn="assistant"]': 115},
        "response_request_binding_required": True,
        "response_request_binding_mode": "prompt_marker",
        "response_request_markers": [token],
        "response_request_marker_count": 1,
        "backend_answer_wait_enabled": True,
        "backend_answer_conversation_id": "conv-123",
        "backend_answer_user_turn_id": "user-node-1",
        "backend_answer_user_turn_index": 1,
    }

    import asyncio

    parsed, selector, text_length, probes = asyncio.run(
        client._try_extract_json_payload(DummyPage(), response_context=context)
    )

    assert parsed == payload
    assert selector == "backend_conversation_detail:assistant_after_user_commit"
    assert text_length > 0
    assert probes[0]["backend_first"] is True
    assert context["last_response_extraction_mode"] == "backend_conversation_after_user_turn_json"
    binding = context["last_response_payload_binding"]
    assert binding["bound_to_post_submit_turn"] is True
    assert binding["turn_selector"] == "backend_conversation_detail"
    assert context["backend_answer_last_status"] == "backend_assistant_turn_after_commit_found"


def test_wait_and_get_json_fast_returns_backend_fresh_marker_payload(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CHATGPT_BACKEND_FIRST_ANSWER_WAIT", "1")
    client = _make_client(tmp_path)
    token = "STALE_GUARD_LIVE_OK_12345678909999999"
    payload = {"ok": True, "sentinel": token, "finished": "finished"}
    calls = {"extract": 0}

    class DummyPage:
        url = "https://chatgpt.com/g/g-p-current-demo/c/conv-123"

        def locator(self, selector):
            raise AssertionError("backend-first success should not require DOM locator polling")

        async def wait_for_timeout(self, ms: int):
            raise AssertionError("backend-first fresh JSON should fast-return without polling")

    async def fake_open(*args, **kwargs):
        return None

    async def fake_fetch(page, *, conversation_id):
        calls["extract"] += 1
        return {
            "ok": True,
            "status": 200,
            "used_authorization": True,
            "payload": {
                "current_node": "assistant-node-1",
                "mapping": {
                    "root": {"parent": None, "message": None},
                    "user-node-1": {
                        "parent": "root",
                        "message": {
                            "author": {"role": "user"},
                            "content": {"parts": ["fresh prompt"]},
                        },
                    },
                    "assistant-node-1": {
                        "parent": "user-node-1",
                        "message": {
                            "author": {"role": "assistant"},
                            "content": {"parts": [json.dumps(payload)]},
                        },
                    },
                },
            },
        }

    async def forbidden_submit_state(page):
        raise AssertionError("fresh backend marker fast-return should skip completion submit-state probe")

    async def forbidden_thinking_state(page):
        raise AssertionError("fresh backend marker fast-return should skip thinking-state probe")

    client._maybe_open_new_project_conversation = fake_open
    client._fetch_conversation_detail = fake_fetch
    client._probe_submit_button_state = forbidden_submit_state
    client._probe_thinking_state = forbidden_thinking_state

    import asyncio
    import time

    context = {
        "response_wait_started_at_monotonic": time.monotonic(),
        "assistant_count": 115,
        "assistant_text": "old stale answer",
        "response_request_binding_required": True,
        "response_request_binding_mode": "prompt_marker",
        "response_request_markers": [token],
        "response_request_marker_count": 1,
        "response_request_nonce_key": "promptbranch_request_nonce",
        "backend_answer_wait_enabled": True,
        "backend_answer_conversation_id": "conv-123",
        "backend_answer_user_turn_id": "user-node-1",
        "backend_answer_user_turn_index": 1,
        "backend_answer_wait_timeout_ms": 120_000,
    }

    answer = asyncio.run(client._wait_and_get_json(DummyPage(), response_context=context))

    assert answer == payload
    assert calls["extract"] == 1
    breakdown = context["response_wait_breakdown"]
    assert breakdown["response_backend_first_answer_wait_enabled"] is True
    assert breakdown["response_freshness_verified"] is True
    assert breakdown["response_freshness_reason"] == "request_marker_match"
    assert breakdown["response_json_fast_return_used"] is True
    assert breakdown["response_json_fast_return_reason"] == "request_marker_match"
    assert context["last_response_extraction_mode"] == "backend_conversation_after_user_turn_json"


def test_backend_answer_wait_timeout_is_bounded_by_service_client_budget(tmp_path: Path, monkeypatch) -> None:
    client = _make_client(tmp_path)
    monkeypatch.setenv("CHATGPT_SERVICE_TIMEOUT_SECONDS", "180")
    monkeypatch.delenv("CHATGPT_SUBMIT_CONFIRMED_ANSWER_TIMEOUT_MS", raising=False)
    monkeypatch.delenv("CHATGPT_SUBMIT_CONFIRMED_ANSWER_TIMEOUT_RESERVE_MS", raising=False)

    submit_evidence = {
        "backend_task_message_evidence": {
            "conversation_id": "conv-123",
            "matched_user_turn_id": "user-node-1",
            "matched_user_turn_index": 42,
        }
    }
    import time

    context: dict[str, object] = {}
    operation_started = time.monotonic() - 45.0
    client._configure_backend_answer_wait_context(
        context,
        submit_evidence=submit_evidence,
        operation_started=operation_started,
    )

    assert context["backend_answer_service_client_budget_ms"] == 180_000
    assert context["backend_answer_timeout_reserve_ms"] == 30_000
    assert context["backend_answer_wait_timeout_ms"] <= 105_000
    assert context["backend_answer_wait_timeout_ms"] >= 90_000
    assert context["ask_operation_elapsed_before_answer_wait_ms"] >= 44_000


def test_backend_answer_probe_records_assistant_turn_qualification_fields(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CHATGPT_BACKEND_FIRST_ANSWER_WAIT", "1")
    client = _make_client(tmp_path)
    payload = {"ok": True, "sentinel": "STALE_GUARD_LIVE_OK_qualification", "finished": "finished"}

    class DummyPage:
        def locator(self, selector):
            raise AssertionError("backend-first extraction must not touch DOM before backend answer probe succeeds")

    async def fake_fetch(page, *, conversation_id):
        return {
            "ok": True,
            "status": 200,
            "used_authorization": True,
            "payload": {
                "current_node": "assistant-node-1",
                "mapping": {
                    "root": {"parent": None, "message": None},
                    "user-node-1": {
                        "parent": "root",
                        "message": {
                            "author": {"role": "user"},
                            "content": {"parts": ["fresh prompt"]},
                            "create_time": 100.0,
                            "update_time": 101.0,
                            "status": "finished_successfully",
                        },
                    },
                    "assistant-node-1": {
                        "parent": "user-node-1",
                        "message": {
                            "author": {"role": "assistant"},
                            "content": {"parts": [json.dumps(payload)], "content_type": "text"},
                            "create_time": 102.0,
                            "update_time": 103.0,
                            "status": "finished_successfully",
                            "end_turn": True,
                        },
                    },
                },
            },
        }

    client._fetch_conversation_detail = fake_fetch
    context = {
        "assistant_count": 115,
        "assistant_text": "old stale answer",
        "response_request_binding_required": True,
        "response_request_binding_mode": "prompt_marker",
        "response_request_markers": ["STALE_GUARD_LIVE_OK_qualification"],
        "response_request_marker_count": 1,
        "backend_answer_wait_enabled": True,
        "backend_answer_conversation_id": "conv-123",
        "backend_answer_user_turn_id": "user-node-1",
        "backend_answer_user_turn_index": 1,
    }

    import asyncio

    parsed, selector, text_length, probes = asyncio.run(
        client._try_extract_json_payload(DummyPage(), response_context=context)
    )

    assert parsed == payload
    assert selector == "backend_conversation_detail:assistant_after_user_commit"
    assert text_length > 0
    assert probes[0]["qualification_status"] == "backend_assistant_after_commit_parseable_json"
    assert probes[0]["assistant_turn_create_time"] == 102.0
    assert probes[0]["assistant_turn_update_time"] == 103.0
    assert probes[0]["assistant_turn_status"] == "finished_successfully"
    assert probes[0]["assistant_turn_end_turn"] is True
    assert probes[0]["assistant_turn_content_type"] == "text"
    assert probes[0]["text_sha256_12"]
    assert context["backend_answer_qualification_status"] == "backend_assistant_after_commit_parseable_json"
    assert context["backend_answer_assistant_turn_create_time"] == 102.0
    assert context["backend_answer_text_sha256_12"] == probes[0]["text_sha256_12"]


def test_response_wait_timing_fields_export_backend_qualification_context(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    context = {
        "response_wait_breakdown": {
            "response_wait_started_at_monotonic": 10.0,
            "response_wait_returned_at_monotonic": 15.0,
            "response_effective_timeout_ms": 90_000,
            "response_backend_first_answer_wait_enabled": True,
        },
        "backend_answer_last_status": "backend_assistant_after_commit_marker_missing",
        "backend_answer_qualification_status": "backend_assistant_after_commit_marker_missing",
        "backend_answer_assistant_turn_id": "assistant-node-1",
        "backend_answer_assistant_turn_index": 2,
        "backend_answer_assistant_turn_create_time": 102.0,
        "backend_answer_assistant_turn_update_time": 103.0,
        "backend_answer_assistant_turn_status": "finished_successfully",
        "backend_answer_text_length": 98,
        "backend_answer_text_sha256_12": "abc123def456",
        "backend_answer_freshness_verified": False,
        "backend_answer_freshness_reason": "request_marker_missing",
        "backend_answer_wait_timeout_ms": 90_000,
        "backend_answer_service_client_budget_ms": 180_000,
        "backend_answer_timeout_reserve_ms": 30_000,
    }

    fields = client._response_wait_timing_fields(
        context,
        response_wait_started_at=10.0,
        response_wait_returned_at=15.0,
    )

    assert fields["response_effective_timeout_ms"] == 90_000
    assert fields["backend_answer_last_status"] == "backend_assistant_after_commit_marker_missing"
    assert fields["backend_answer_qualification_status"] == "backend_assistant_after_commit_marker_missing"
    assert fields["backend_answer_assistant_turn_id"] == "assistant-node-1"
    assert fields["backend_answer_assistant_turn_status"] == "finished_successfully"
    assert fields["backend_answer_freshness_reason"] == "request_marker_missing"
    assert fields["backend_answer_service_client_budget_ms"] == 180_000


def test_backend_answer_wait_budget_prefers_explicit_client_timeout_over_environment(tmp_path: Path, monkeypatch) -> None:
    client = _make_client(tmp_path)
    monkeypatch.setenv("CHATGPT_SERVICE_TIMEOUT_SECONDS", "900")
    monkeypatch.delenv("CHATGPT_SUBMIT_CONFIRMED_ANSWER_TIMEOUT_MS", raising=False)
    monkeypatch.delenv("CHATGPT_SUBMIT_CONFIRMED_ANSWER_TIMEOUT_RESERVE_MS", raising=False)

    submit_evidence = {
        "backend_task_message_evidence": {
            "conversation_id": "conv-123",
            "matched_user_turn_id": "user-node-1",
            "matched_user_turn_index": 42,
        }
    }
    import time

    context: dict[str, object] = {}
    operation_started = time.monotonic() - 45.0
    ask_deadline = client._ask_operation_deadline_monotonic(
        operation_started=operation_started,
        service_timeout_seconds=180.0,
    )
    client._configure_backend_answer_wait_context(
        context,
        submit_evidence=submit_evidence,
        operation_started=operation_started,
        service_timeout_seconds=180.0,
        ask_deadline_monotonic=ask_deadline,
    )

    assert context["backend_answer_service_client_budget_ms"] == 180_000
    assert context["service_timeout_seconds"] == 180.0
    assert context["backend_answer_wait_timeout_ms"] <= 105_000
    assert context["backend_answer_wait_timeout_ms"] >= 90_000
    assert context["ask_operation_deadline_remaining_ms_at_answer_wait_config"] <= 105_000


def test_response_effective_timeout_is_capped_by_absolute_ask_deadline(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    import time

    context: dict[str, object] = {
        "backend_answer_wait_enabled": True,
        "backend_answer_conversation_id": "conv-123",
        "backend_answer_user_turn_id": "user-node-1",
        "backend_answer_user_turn_index": 1,
        "backend_answer_wait_timeout_ms": 120_000,
        "ask_operation_deadline_monotonic": time.monotonic() + 42.0,
    }

    effective_timeout_ms = client._response_effective_timeout_ms(context)

    assert 35_000 <= effective_timeout_ms <= 42_000
    assert context["ask_operation_deadline_remaining_ms_at_json_wait_start"] <= 42_000


def test_backend_marker_missing_candidate_falls_through_to_dom_visible_answer(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CHATGPT_BACKEND_FIRST_ANSWER_WAIT", "1")
    client = _make_client(tmp_path)
    fresh_token = "STALE_GUARD_LIVE_OK_dom_compare"
    backend_payload = {"ok": True, "sentinel": "OLD_BACKEND_CANDIDATE", "finished": "finished"}
    dom_payload = {"ok": True, "sentinel": fresh_token, "finished": "finished"}

    async def fake_fetch(page, *, conversation_id):
        return {
            "ok": True,
            "status": 200,
            "used_authorization": True,
            "payload": {
                "current_node": "assistant-node-1",
                "mapping": {
                    "root": {"parent": None, "message": None},
                    "user-node-1": {
                        "parent": "root",
                        "message": {"author": {"role": "user"}, "content": {"parts": ["fresh prompt"]}},
                    },
                    "assistant-node-1": {
                        "parent": "user-node-1",
                        "message": {"author": {"role": "assistant"}, "content": {"parts": [json.dumps(backend_payload)]}},
                    },
                }
            },
        }

    class DummyJsonItem:
        def __init__(self, text: str) -> None:
            self.text = text

        async def is_visible(self, timeout=None):
            return True

        async def inner_text(self, timeout=None):
            return self.text

        async def text_content(self, timeout=None):
            return ""

    class ScopedJsonLocator:
        def __init__(self, text: str) -> None:
            self.text = text

        @property
        def last(self):
            return DummyJsonItem(self.text)

        async def count(self):
            return 1

    class AssistantTurn:
        def __init__(self, text: str) -> None:
            self.text = text

        def locator(self, selector):
            return ScopedJsonLocator(self.text)

        async def inner_text(self, timeout=None):
            return self.text

        async def text_content(self, timeout=None):
            return ""

        async def is_visible(self, timeout=None):
            return True

    class AssistantLocator:
        def __init__(self) -> None:
            self.turns = [
                AssistantTurn('{"ok": true, "sentinel": "OLD_PRE_SUBMIT"}'),
                AssistantTurn(json.dumps(dom_payload)),
            ]

        async def count(self):
            return len(self.turns)

        def nth(self, index: int):
            return self.turns[index]

        @property
        def last(self):
            return self.turns[-1]

    class EmptyLocator:
        async def count(self):
            return 0

        def nth(self, index: int):
            raise AssertionError("empty selector should not be indexed")

    class DummyPage:
        def locator(self, selector):
            if selector == 'section[data-turn="assistant"]':
                return AssistantLocator()
            return EmptyLocator()

    client._fetch_conversation_detail = fake_fetch
    context = {
        "assistant_selector": 'section[data-turn="assistant"]',
        "assistant_count": 1,
        "assistant_text": '{"ok": true, "sentinel": "OLD_PRE_SUBMIT"}',
        "assistant_turn_baseline_counts": {'section[data-turn="assistant"]': 1},
        "response_request_binding_required": True,
        "response_request_binding_mode": "prompt_marker",
        "response_request_markers": [fresh_token],
        "response_request_marker_count": 1,
        "backend_answer_wait_enabled": True,
        "backend_answer_conversation_id": "conv-123",
        "backend_answer_user_turn_id": "user-node-1",
        "backend_answer_user_turn_index": 1,
    }

    import asyncio

    parsed, selector, text_length, probes = asyncio.run(
        client._try_extract_json_payload(DummyPage(), response_context=context)
    )

    assert parsed == dom_payload
    assert selector == 'section[data-turn="assistant"]:nth(1) >> #code-block-viewer .cm-content'
    assert text_length > 0
    assert context["backend_answer_marker_missing_fell_through_to_dom"] is True
    assert context["response_extraction_accepted_source"] == "dom_post_submit_code"
    candidates = context["response_extraction_candidates"]
    assert [candidate["source"] for candidate in candidates] == ["backend_conversation_detail", "dom_post_submit_code"]
    assert candidates[0]["accepted"] is False
    assert candidates[0]["rejected_reason"] == "request_marker_missing"
    assert candidates[1]["accepted"] is True
    assert candidates[1]["contains_request_marker"] is True


def test_wait_and_get_json_skips_final_debug_when_hard_deadline_exhausted(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client.config.debug = True

    class DummyPage:
        url = "https://chatgpt.com/g/g-p-current-demo/c/test-conversation"

        async def wait_for_timeout(self, ms: int):
            raise AssertionError("hard deadline should stop before sleeping")

    async def forbidden_open(*args, **kwargs):
        raise AssertionError("hard deadline should skip project conversation opening")

    async def forbidden_extract(*args, **kwargs):
        raise AssertionError("hard deadline should skip extraction")

    async def forbidden_submit_state(*args, **kwargs):
        raise AssertionError("hard deadline should skip submit-state probing")

    async def forbidden_debug(*args, **kwargs):
        raise AssertionError("hard deadline should skip debug artifacts")

    client._maybe_open_new_project_conversation = forbidden_open
    client._try_extract_json_payload = forbidden_extract
    client._probe_submit_button_state = forbidden_submit_state
    client._save_response_diagnostics = forbidden_debug

    import asyncio
    import time
    from promptbranch_browser_auth.exceptions import ResponseTimeoutError

    context = {
        "response_wait_started_at_monotonic": time.monotonic(),
        "ask_operation_deadline_monotonic": time.monotonic() + 0.001,
        "backend_answer_wait_enabled": True,
        "backend_answer_conversation_id": "conv-123",
        "backend_answer_user_turn_id": "user-node-1",
        "backend_answer_user_turn_index": 1,
        "submit_confirmed": True,
    }

    try:
        asyncio.run(client._wait_and_get_json(DummyPage(), response_context=context))
    except ResponseTimeoutError as exc:
        assert "submit_confirmed_answer_timeout" in str(exc)
    else:
        raise AssertionError("expected response timeout")

    breakdown = context["response_wait_breakdown"]
    assert breakdown["response_deadline_hard_stop"] is True
    assert breakdown["response_final_probe_skipped_due_to_deadline"] is True
    assert breakdown["response_timeout_debug_artifact_skipped_due_to_deadline"] is True


def test_promotes_fresh_json_from_post_submit_visibility_generic_turn(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    marker = "STALE_GUARD_LIVE_OK_1780009919490820134"
    response_context = {
        "response_request_binding_required": True,
        "response_request_markers": [marker],
        "response_request_nonce_key": "promptbranch_request_nonce",
        "pre_submit_payload_hashes": [],
    }
    submit_evidence = {
        "post_submit_user_turn_visibility_evidence": {
            "state": {
                "last_text_preview": f'Return exactly this JSON object: {{"ok": true, "sentinel": "{marker}", "finished": "finished"}}.',
                "generic_turns": {
                    "last_text_preview": f'JSON\n{{"ok":true,"sentinel":"{marker}","finished":"finished"}}',
                },
            }
        }
    }

    promoted = client._promote_visible_answer_from_submit_evidence(
        submit_evidence=submit_evidence,
        response_context=response_context,
        extraction_started=0.0,
    )

    assert promoted is not None
    assert promoted["payload"] == {"ok": True, "sentinel": marker, "finished": "finished"}
    assert promoted["source"] == "post_submit_visibility_generic_turn"
    assert response_context["response_extraction_accepted_source"] == "post_submit_visibility_generic_turn"
    assert response_context["last_response_payload_binding"]["bound_to_post_submit_turn"] is True


def test_does_not_promote_prompt_echo_from_visibility_evidence(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    marker = "STALE_GUARD_LIVE_OK_1780009919490820134"
    response_context = {
        "response_request_binding_required": True,
        "response_request_markers": [marker],
        "response_request_nonce_key": "promptbranch_request_nonce",
        "pre_submit_payload_hashes": [],
    }
    submit_evidence = {
        "post_submit_user_turn_visibility_evidence": {
            "state": {
                "last_text_preview": f'Return exactly this JSON object: {{"ok": true, "sentinel": "{marker}", "finished": "finished"}}. JSON GENERATION STRICT RULES:',
            }
        }
    }

    promoted = client._promote_visible_answer_from_submit_evidence(
        submit_evidence=submit_evidence,
        response_context=response_context,
        extraction_started=0.0,
    )

    assert promoted is None
    assert "response_extraction_accepted_source" not in response_context


def test_fast_latest_visible_answer_promotion_prefers_latest_assistant_turn(tmp_path: Path) -> None:
    import asyncio

    client = _make_client(tmp_path)
    marker = "STALE_GUARD_LIVE_OK_1780010958856819059"
    response_context = {
        "response_request_binding_required": True,
        "response_request_markers": [marker],
        "response_request_nonce_key": "promptbranch_request_nonce",
        "pre_submit_payload_hashes": [],
    }

    class DummyElement:
        def __init__(self, text: str) -> None:
            self._text = text

        async def inner_text(self, timeout=None):
            return self._text

    class DummyLocator:
        def __init__(self, texts):
            self._texts = list(texts)

        async def count(self):
            return len(self._texts)

        def nth(self, index):
            return DummyElement(self._texts[index])

    class DummyPage:
        def locator(self, selector):
            if selector == '[data-message-author-role="assistant"]':
                return DummyLocator([
                    'JSON\n{"ok":true,"sentinel":"OLD","finished":"finished"}',
                    f'JSON\n{{"ok":true,"sentinel":"{marker}","finished":"finished"}}',
                ])
            return DummyLocator([])

    promoted = asyncio.run(client._promote_fast_latest_visible_answer(
        DummyPage(),
        response_context=response_context,
        extraction_started=0.0,
    ))

    assert promoted is not None
    assert promoted["payload"] == {"ok": True, "sentinel": marker, "finished": "finished"}
    assert promoted["source"] == "fast_latest_assistant_turn"
    assert response_context["response_extraction_accepted_source"] == "fast_latest_assistant_turn"
    assert response_context["last_response_payload_binding"]["bound_to_post_submit_turn"] is True


def test_fast_latest_visible_answer_rejects_prompt_echo(tmp_path: Path) -> None:
    import asyncio

    client = _make_client(tmp_path)
    marker = "STALE_GUARD_LIVE_OK_1780010958856819059"
    response_context = {
        "response_request_binding_required": True,
        "response_request_markers": [marker],
        "response_request_nonce_key": "promptbranch_request_nonce",
        "pre_submit_payload_hashes": [],
    }

    class DummyElement:
        def __init__(self, text: str) -> None:
            self._text = text

        async def inner_text(self, timeout=None):
            return self._text

    class DummyLocator:
        async def count(self):
            return 1

        def nth(self, index):
            return DummyElement(
                f'Return exactly this JSON object: {{"ok": true, "sentinel": "{marker}", "finished": "finished"}}. JSON GENERATION STRICT RULES:'
            )

    class DummyPage:
        def locator(self, selector):
            if selector == '[data-message-author-role="assistant"]':
                return DummyLocator()
            return type('EmptyLocator', (), {
                'count': lambda self: asyncio.sleep(0, result=0),
            })()

    promoted = asyncio.run(client._promote_fast_latest_visible_answer(
        DummyPage(),
        response_context=response_context,
        extraction_started=0.0,
    ))

    assert promoted is None
    assert "response_extraction_accepted_source" not in response_context


def test_keyboard_submit_diagnostics_are_observational(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class DummyPage:
        def __init__(self):
            self.calls = []

        async def evaluate(self, script, arg):
            self.calls.append((script, arg))
            return {
                "status": "captured",
                "label": arg["label"],
                "active_element": {"present": True, "tag_name": "div", "exact_marker_found": True},
                "composer": {"present": True, "text_length": 80, "exact_marker_found": True},
                "send_button": {"present": True, "send_ready": True},
            }

    import asyncio

    page = DummyPage()
    result = asyncio.run(client._capture_keyboard_submit_diagnostics(
        page,
        prompt='Return {"sentinel":"STALE_GUARD_LIVE_OK_1780017000000000000"}',
        label="unit:pre_dispatch",
    ))

    assert result["status"] == "captured"
    assert result["label"] == "unit:pre_dispatch"
    assert result["requested_exact_marker_count"] == 1
    assert result["active_element"]["exact_marker_found"] is True
    assert page.calls[0][1]["label"] == "unit:pre_dispatch"


def test_keyboard_submit_variant_records_diagnostics_without_changing_dispatch(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class DummyKeyboard:
        def __init__(self):
            self.pressed = []

        async def press(self, key):
            self.pressed.append(key)

    class DummyPage:
        def __init__(self):
            self.keyboard = DummyKeyboard()

        async def evaluate(self, script, arg):
            if isinstance(arg, dict):
                return {
                    "status": "captured",
                    "label": arg["label"],
                    "composer": {"present": True, "exact_marker_found": True},
                    "send_button": {"present": True, "send_ready": True},
                }
            if "event_count" in script:
                return {"collected": True, "label": arg, "event_count": 1, "events": [{"type": "keydown", "key": "Enter"}]}
            return {"installed": True, "label": arg, "event_types": ["keydown"]}

    async def fake_find(page):
        return object(), "#prompt-textarea"

    async def fake_fill(page, input_locator, *, prompt):
        return {
            "method": "trusted_paste",
            "requested_method": "trusted_paste",
            "verification_passed": True,
            "trusted_input_used": True,
            "duration_seconds": 0.01,
        }

    async def fake_wait(page, *, before_assistant_count, before_user_turn_state, prompt, submit_network_observer):
        return {
            "confirmed": True,
            "confirmed_by": ["network_submit_request"],
            "confirmation_mode": "network_submit_request",
            "submit_network_evidence": {
                "status": "submit_network_request_observed",
                "message_request_observed": True,
                "message_request_count": 1,
            },
        }

    async def fake_after(page, *, prompt):
        return {"text_length": 0}

    page = DummyPage()
    client._find_visible_chat_input_for_submit_variant = fake_find
    client._fill_chat_prompt = fake_fill
    client._start_submit_network_observer = lambda page, prompt=None: {"observer": True}
    client._stop_submit_network_observer = lambda page, observer: None
    client._wait_for_submit_confirmation = fake_wait
    client._capture_post_submit_composer_state = fake_after

    import asyncio

    result = asyncio.run(client._run_keyboard_submit_variant(
        page,
        prompt='Return {"sentinel":"STALE_GUARD_LIVE_OK_1780017000000000001"}',
        before_assistant_count=0,
        before_user_turn_state={},
        variant="keyboard_enter_refill_retry",
        dispatch_key="Enter",
    ))

    assert page.keyboard.pressed == ["Enter"]
    assert result["confirmed"] is True
    assert result["diagnostic_submit_path"] == "v0.0.278.48_observational_only"
    assert result["fill_call_site_timing"]["diagnostic_timing_path"] == "v0.0.278.52_call_site_only_fill_timing"
    assert result["fill_call_site_timing"]["duration_seconds"] == result["fill_seconds"]
    assert "monotonic_timing" not in result["fill_evidence"]
    assert result["before_fill_diagnostics"]["label"] == "keyboard_enter_refill_retry:before_fill"
    assert result["after_fill_diagnostics"]["label"] == "keyboard_enter_refill_retry:after_fill"
    assert result["pre_dispatch_diagnostics"]["label"] == "keyboard_enter_refill_retry:pre_dispatch"
    assert result["keyboard_event_probe_install"]["installed"] is True
    assert result["keyboard_event_probe_events"]["event_count"] == 1
