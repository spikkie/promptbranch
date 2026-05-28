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
        prompt="Return exactly this JSON object",
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
            "prompt_prefix_found": True,
            "generic_turns": {"request_id_found": False, "prompt_prefix_found": False},
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
        prompt="Return exactly this JSON object",
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

