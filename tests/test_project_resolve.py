from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import chatgpt_browser_auth.client as client_module
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


class FakeClickable:
    def __init__(self) -> None:
        self.click_count = 0
        self.scroll_count = 0

    async def click(self, *args, **kwargs) -> None:
        self.click_count += 1

    async def scroll_into_view_if_needed(self, *args, **kwargs) -> None:
        self.scroll_count += 1


def test_project_add_source_button_selectors_cover_empty_state_add_button(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    assert any('button:has-text("Add")' in selector for selector in client_module.PROJECT_ADD_SOURCE_BUTTON_SELECTORS)


async def _run_remove_project_retry_harness(client: ChatGPTBrowserClient, page: FakePage):
    return await client._remove_project_operation(context=None, page=page)


def test_remove_project_retries_sidebar_lookup_and_uses_project_id_identity(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client.config.project_url = 'https://chatgpt.com/g/g-p-69de540eadf88191b04ad8fd42ec8835/project'
    page = FakePage()

    calls: list[str] = []
    delete_action = FakeClickable()
    confirm_action = FakeClickable()
    options_button = FakeClickable()
    containers = iter([None, None, object()])
    seen_project_urls: list[str | None] = []

    async def fake_ensure_logged_in(*_args, **_kwargs) -> None:
        return None

    async def fake_goto(*_args, **_kwargs) -> None:
        return None

    async def fake_ensure_sidebar_open(*_args, **_kwargs) -> None:
        return None

    async def fake_expand_projects_section(*_args, **_kwargs) -> bool:
        calls.append('expand')
        return True

    async def fake_prime_project_sidebar(*_args, **_kwargs) -> None:
        calls.append('prime')
        return None

    async def fake_find_project_sidebar_container(*_args, **kwargs):
        seen_project_urls.append(kwargs.get('project_url'))
        return next(containers)

    async def fake_find_project_options_button(_container):
        return options_button

    async def fake_wait_for_visible_locator(_page, _selectors, *, label: str, **_kwargs):
        if label == 'project-remove-action':
            return delete_action
        if label == 'project-remove-confirm':
            return confirm_action
        raise AssertionError(f'unexpected locator label: {label}')

    async def fake_wait_for_project_absence(*_args, **_kwargs) -> None:
        return None

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return 'https://chatgpt.com/'

    client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    client._goto = fake_goto  # type: ignore[method-assign]
    client._ensure_sidebar_open = fake_ensure_sidebar_open  # type: ignore[method-assign]
    client._expand_projects_section = fake_expand_projects_section  # type: ignore[method-assign]
    client._prime_project_sidebar = fake_prime_project_sidebar  # type: ignore[method-assign]
    client._find_project_sidebar_container = fake_find_project_sidebar_container  # type: ignore[method-assign]
    client._find_project_options_button = fake_find_project_options_button  # type: ignore[method-assign]
    client._wait_for_visible_locator = fake_wait_for_visible_locator  # type: ignore[method-assign]
    client._wait_for_project_absence = fake_wait_for_project_absence  # type: ignore[method-assign]
    client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]

    result = asyncio.run(_run_remove_project_retry_harness(client, page))

    assert calls == ['expand', 'prime', 'expand']
    assert seen_project_urls == [
        'https://chatgpt.com/g/g-p-69de540eadf88191b04ad8fd42ec8835/project',
        'https://chatgpt.com/g/g-p-69de540eadf88191b04ad8fd42ec8835/project',
        'https://chatgpt.com/g/g-p-69de540eadf88191b04ad8fd42ec8835/project',
    ]
    assert options_button.click_count == 1
    assert delete_action.click_count == 1
    assert confirm_action.click_count == 1
    assert result['deleted_project_id'] == 'g-p-69de540eadf88191b04ad8fd42ec8835'



def test_is_logged_in_treats_project_page_without_composer_as_authenticated(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    page = FakePage()

    async def fake_find_visible_locator(*_args, **_kwargs):
        return None

    async def fake_has_chat_input(*_args, **_kwargs) -> bool:
        return False

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return 'https://chatgpt.com/g/g-p-69de540eadf88191b04ad8fd42ec8835/project'

    client._find_visible_locator = fake_find_visible_locator  # type: ignore[method-assign]
    client._has_chat_input = fake_has_chat_input  # type: ignore[method-assign]
    client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]

    assert asyncio.run(client._is_logged_in(page)) is True


def test_link_source_kind_uses_capability_probe_without_text_fallback(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    assert client._project_source_option_kinds('link') == ['link']
    summary = client._project_source_capability_summary(['Upload', 'Text input', 'Google Drive', 'Slack'])
    assert [item['kind'] for item in summary] == ['file', 'text', 'gdrive', 'slack']


def test_remove_project_uses_project_details_menu_when_current_page_matches(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client.config.project_url = 'https://chatgpt.com/g/g-p-69de540eadf88191b04ad8fd42ec8835/project'
    page = FakePage()

    details_button = FakeClickable()
    delete_action = FakeClickable()
    confirm_action = FakeClickable()
    sidebar_calls = 0

    async def fake_ensure_logged_in(*_args, **_kwargs) -> None:
        return None

    async def fake_goto(*_args, **_kwargs) -> None:
        return None

    async def fake_ensure_sidebar_open(*_args, **_kwargs) -> None:
        return None

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return 'https://chatgpt.com/g/g-p-69de540eadf88191b04ad8fd42ec8835/project'

    async def fake_find_visible_locator(_page, _selectors, *, label: str, **_kwargs):
        if label == 'project-page-details-menu':
            return details_button
        return None

    async def fake_wait_for_visible_locator(_page, _selectors, *, label: str, **_kwargs):
        if label == 'project-remove-action':
            return delete_action
        if label == 'project-remove-confirm':
            return confirm_action
        raise AssertionError(f'unexpected locator label: {label}')

    async def fake_find_project_sidebar_container(*_args, **_kwargs):
        nonlocal sidebar_calls
        sidebar_calls += 1
        raise AssertionError('sidebar lookup should not be used when project details menu succeeds')

    async def fake_wait_for_project_absence(*_args, **_kwargs) -> None:
        return None

    client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    client._goto = fake_goto  # type: ignore[method-assign]
    client._ensure_sidebar_open = fake_ensure_sidebar_open  # type: ignore[method-assign]
    client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    client._find_visible_locator = fake_find_visible_locator  # type: ignore[method-assign]
    client._wait_for_visible_locator = fake_wait_for_visible_locator  # type: ignore[method-assign]
    client._find_project_sidebar_container = fake_find_project_sidebar_container  # type: ignore[method-assign]
    client._wait_for_project_absence = fake_wait_for_project_absence  # type: ignore[method-assign]

    result = asyncio.run(_run_remove_project_retry_harness(client, page))

    assert details_button.click_count == 1
    assert delete_action.click_count == 1
    assert confirm_action.click_count == 1
    assert sidebar_calls == 0
    assert result['deleted_project_id'] == 'g-p-69de540eadf88191b04ad8fd42ec8835'




def test_project_source_option_kinds_link_does_not_fallback_to_text(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    assert client._project_source_option_kinds("link") == ["link"]


def test_wait_for_source_presence_accepts_single_new_text_card_when_rendered_identity_differs(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    page = FakePage()

    snapshots = iter(
        [
            [],
            [
                {
                    "text": "Integration note for run 20260414-224024-896.txt Document",
                    "key": "integration note for run 20260414-224024-896.txt document",
                }
            ],
        ]
    )

    async def fake_snapshot_project_source_cards(_page):
        return next(snapshots)

    async def fake_find_project_source_container(*_args, **_kwargs):
        return None

    client._snapshot_project_source_cards = fake_snapshot_project_source_cards  # type: ignore[method-assign]
    client._find_project_source_container = fake_find_project_source_container  # type: ignore[method-assign]

    result = asyncio.run(
        client._wait_for_source_presence(
            page,
            source_match_candidates=[
                "Integration note for run 20260414-224024-896",
                "Integration note for run 20260414-223908-2242442",
            ],
            before_sources=[],
            accept_single_new_card=True,
            timeout_ms=2_000,
        )
    )

    assert result == {
        "text": "Integration note for run 20260414-224024-896.txt Document",
        "key": "integration note for run 20260414-224024-896.txt document",
    }

def test_text_source_match_candidates_prefer_rendered_body_preview_over_display_name(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    candidates = client._build_source_match_candidates(
        "text",
        value="Integration note for run 20260414-220546-2113931",
        display_name="itest-text-20260414-220546-2113931",
        file_path=None,
    )

    assert candidates[0] == "Integration note for run 20260414-220546-2113931"
    assert "itest-text-20260414-220546-2113931" in candidates


def test_wait_for_source_presence_accepts_actual_rendered_text_source_card_identity(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    page = FakePage()

    snapshots = iter(
        [
            [],
            [
                {
                    "text": "Integration note for run 20260414-220546-2113931",
                    "key": "integration note for run 20260414-220546-2113931",
                }
            ],
        ]
    )

    async def fake_snapshot_project_source_cards(_page):
        return next(snapshots)

    async def fake_find_project_source_container(*_args, **_kwargs):
        return None

    client._snapshot_project_source_cards = fake_snapshot_project_source_cards  # type: ignore[method-assign]
    client._find_project_source_container = fake_find_project_source_container  # type: ignore[method-assign]

    result = asyncio.run(
        client._wait_for_source_presence(
            page,
            source_match_candidates=[
                "Integration note for run 20260414-220546-2113931",
                "itest-text-20260414-220546-2113931",
            ],
            before_sources=[],
            timeout_ms=2_000,
        )
    )

    assert result == {
        "text": "Integration note for run 20260414-220546-2113931",
        "key": "integration note for run 20260414-220546-2113931",
    }
