from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import pytest

import promptbranch_browser_auth.client as client_module
from promptbranch_browser_auth.client import ChatGPTBrowserClient
from promptbranch_browser_auth.config import ChatGPTBrowserConfig
from promptbranch_browser_auth.exceptions import AuthChallengeRequiredError


@dataclass
class FakePage:
    evaluate_result: object | None = None

    async def evaluate(self, _script: str):
        return self.evaluate_result

    async def evaluate_handle(self, _script: str, _args=None):
        class _Handle:
            def as_element(self):
                return None
        return _Handle()

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


def test_private_remove_project_operation_is_blocked_before_ui_actions(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client.config.project_url = 'https://chatgpt.com/g/g-p-69de540eadf88191b04ad8fd42ec8835/project'
    page = FakePage()

    async def forbidden(*_args, **_kwargs):  # pragma: no cover - should not be reached
        raise AssertionError('project remove operation must not touch ChatGPT UI')

    client.ensure_logged_in = forbidden  # type: ignore[method-assign]
    client._goto = forbidden  # type: ignore[method-assign]
    client._ensure_sidebar_open = forbidden  # type: ignore[method-assign]

    result = asyncio.run(_run_remove_project_retry_harness(client, page))

    assert result['ok'] is False
    assert result['status'] == 'project_delete_disabled'
    assert result['blocked_at_layer'] == 'browser_client_operation'
    assert result['destructive_action_executed'] is False


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


def test_match_source_card_prefers_structured_identity_fields(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    card = {
        "text": "pasted.txt Document · Apr 16, 2026",
        "key": "pasted.txt document",
        "title": "pasted.txt",
        "subtitle": "Document · Apr 16, 2026",
        "identity": "pasted.txt Document",
    }

    assert client._match_source_card([card], ["pasted.txt Document"]) == card
    assert client._match_source_card([card], ["pasted.txt"]) == card



def test_match_source_card_ignores_shared_file_placeholder_metadata_for_lookup(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    sibling_card = {
        "text": "fixture-source-b.zip File contents may not be accessible",
        "key": "fixture-source-b.zip",
        "title": "fixture-source-b.zip",
        "subtitle": "File contents may not be accessible",
        "identity": "fixture-source-b.zip File contents may not be accessible",
    }

    assert client._match_source_card(
        [sibling_card],
        [
            "fixture-source-a.zip",
            "fixture-source-a.zip File contents may not be accessible",
        ],
        anchor_safe=True,
    ) is None



def test_source_lookup_candidates_include_structured_card_identity(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    card = {
        "text": "pasted.txt Document · Apr 16, 2026",
        "key": "pasted.txt document",
        "title": "pasted.txt",
        "subtitle": "Document · Apr 16, 2026",
        "identity": "pasted.txt Document",
    }

    candidates = client._source_lookup_candidates("pasted.txt Document", card)

    assert candidates[0] == "pasted.txt Document"
    assert "pasted.txt" in candidates
    assert "Document · Apr 16, 2026" in candidates


def test_source_lookup_candidates_exact_safe_excludes_shared_metadata_only_values(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    card = {
        "text": "fixture-source-a.zip File contents may not be accessible",
        "key": "fixture-source-a.zip",
        "title": "fixture-source-a.zip",
        "subtitle": "File contents may not be accessible",
        "identity": "fixture-source-a.zip File contents may not be accessible",
    }

    candidates = client._source_lookup_candidates(
        "fixture-source-a.zip",
        card,
        exact_safe=True,
    )

    assert candidates == [
        "fixture-source-a.zip",
        "fixture-source-a.zip File contents may not be accessible",
    ]


def test_source_lookup_candidates_anchor_safe_excludes_shared_metadata_only_values(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    card = {
        "text": "fixture-source-a.zip File contents may not be accessible",
        "key": "fixture-source-a.zip",
        "title": "fixture-source-a.zip",
        "subtitle": "File contents may not be accessible",
        "identity": "fixture-source-a.zip File contents may not be accessible",
    }

    candidates = client._source_lookup_candidates(
        "fixture-source-a.zip",
        card,
        anchor_safe=True,
    )

    assert candidates == [
        "fixture-source-a.zip",
        "fixture-source-a.zip File contents may not be accessible",
    ]


def test_project_source_stable_absence_accepts_empty_sources_surface(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    page = FakePage()

    async def fake_snapshot_project_source_cards(_page):
        return []

    async def fake_find_project_source_action_button(*_args, **_kwargs):
        return None

    async def fake_find_project_source_container(*_args, **_kwargs):
        return None

    async def fake_project_sources_empty_state_visible(_page):
        return True

    client._snapshot_project_source_cards = fake_snapshot_project_source_cards  # type: ignore[method-assign]
    client._find_project_source_action_button = fake_find_project_source_action_button  # type: ignore[method-assign]
    client._find_project_source_container = fake_find_project_source_container  # type: ignore[method-assign]
    client._project_sources_empty_state_visible = fake_project_sources_empty_state_visible  # type: ignore[method-assign]

    result = asyncio.run(
        client._project_source_is_stably_absent(
            page,
            ["pasted.txt Document"],
            exact=True,
            required_observations=2,
            poll_interval_ms=1,
        )
    )

    assert result is True



def test_project_source_stable_absence_accepts_non_empty_unmatched_surface(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    page = FakePage()

    async def fake_snapshot_project_source_cards(_page):
        return [
            {
                "text": "itest-file-20260417-131136-2837993.txt Document · Apr 17, 2026",
                "key": "itest-file-20260417-131136-2837993.txt document",
                "title": "itest-file-20260417-131136-2837993.txt",
                "subtitle": "Document · Apr 17, 2026",
                "identity": "itest-file-20260417-131136-2837993.txt Document",
            }
        ]

    async def fake_find_project_source_action_button(*_args, **_kwargs):
        return None

    async def fake_find_project_source_container(*_args, **_kwargs):
        return None

    async def fake_project_sources_empty_state_visible(_page):
        return False

    client._snapshot_project_source_cards = fake_snapshot_project_source_cards  # type: ignore[method-assign]
    client._find_project_source_action_button = fake_find_project_source_action_button  # type: ignore[method-assign]
    client._find_project_source_container = fake_find_project_source_container  # type: ignore[method-assign]
    client._project_sources_empty_state_visible = fake_project_sources_empty_state_visible  # type: ignore[method-assign]

    result = asyncio.run(
        client._project_source_is_stably_absent(
            page,
            ["pasted.txt Document"],
            exact=True,
            required_observations=2,
            poll_interval_ms=1,
        )
    )

    assert result is True





class FakeClickFailsThenForceSucceeds(FakeClickable):
    def __init__(self) -> None:
        super().__init__()
        self.force_click_count = 0

    async def click(self, *args, **kwargs) -> None:
        self.click_count += 1
        if kwargs.get("force"):
            self.force_click_count += 1
            return None
        raise RuntimeError("pointer intercepted")


def test_wait_for_project_source_action_button_exact_uses_exact_safe_candidates(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    page = FakePage()

    captured_candidates: list[list[str]] = []
    sentinel_button = object()

    async def fake_snapshot_project_source_cards(*_args, **_kwargs):
        return [
            {
                "text": "fixture-source-a.zip File contents may not be accessible",
                "key": "fixture-source-a.zip",
                "title": "fixture-source-a.zip",
                "subtitle": "File contents may not be accessible",
                "identity": "fixture-source-a.zip File contents may not be accessible",
            }
        ]

    async def fake_find_project_source_action_button_for_card(_page, matched_card):
        captured_candidates.append(client._source_lookup_candidates("fixture-source-a.zip", matched_card, exact_safe=True, anchor_safe=True))
        return sentinel_button

    async def fake_find_project_source_action_button(_page, source_names, *, exact: bool):
        raise AssertionError("exact source removal must not use the broad action-button fallback")

    async def fake_project_sources_empty_state_visible(*_args, **_kwargs):
        return False

    async def fake_safe_page_url(*_args, **_kwargs):
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    client._snapshot_project_source_cards = fake_snapshot_project_source_cards  # type: ignore[method-assign]
    client._find_project_source_action_button_for_card = fake_find_project_source_action_button_for_card  # type: ignore[method-assign]
    client._find_project_source_action_button = fake_find_project_source_action_button  # type: ignore[method-assign]
    client._project_sources_empty_state_visible = fake_project_sources_empty_state_visible  # type: ignore[method-assign]
    client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]

    action_button, matched_card, candidates = asyncio.run(
        client._wait_for_project_source_action_button(
            page,
            ["fixture-source-a.zip"],
            exact=True,
            timeout_ms=1_000,
            poll_interval_ms=1,
        )
    )

    assert action_button is sentinel_button
    assert matched_card == {
        "text": "fixture-source-a.zip File contents may not be accessible",
        "key": "fixture-source-a.zip",
        "title": "fixture-source-a.zip",
        "subtitle": "File contents may not be accessible",
        "identity": "fixture-source-a.zip File contents may not be accessible",
    }
    assert captured_candidates == [[
        "fixture-source-a.zip",
        "fixture-source-a.zip File contents may not be accessible",
    ]]
    assert candidates == [
        "fixture-source-a.zip",
        "fixture-source-a.zip File contents may not be accessible",
    ]


def test_wait_for_project_source_action_button_non_exact_anchors_retry_candidates(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    page = FakePage()

    captured_candidates: list[list[str]] = []
    sentinel_button = object()

    async def fake_snapshot_project_source_cards(*_args, **_kwargs):
        return [
            {
                "text": "fixture-source-a.zip File contents may not be accessible",
                "key": "fixture-source-a.zip",
                "title": "fixture-source-a.zip",
                "subtitle": "File contents may not be accessible",
                "identity": "fixture-source-a.zip File contents may not be accessible",
            }
        ]

    async def fake_find_project_source_action_button(_page, source_names, *, exact: bool):
        captured_candidates.append(list(source_names))
        assert exact is False
        return sentinel_button

    async def fake_project_sources_empty_state_visible(*_args, **_kwargs):
        return False

    async def fake_safe_page_url(*_args, **_kwargs):
        return "https://chatgpt.com/g/g-p-123/project?tab=sources"

    client._snapshot_project_source_cards = fake_snapshot_project_source_cards  # type: ignore[method-assign]
    client._find_project_source_action_button = fake_find_project_source_action_button  # type: ignore[method-assign]
    client._project_sources_empty_state_visible = fake_project_sources_empty_state_visible  # type: ignore[method-assign]
    client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]

    action_button, matched_card, candidates = asyncio.run(
        client._wait_for_project_source_action_button(
            page,
            ["fixture-source-a.zip"],
            exact=False,
            timeout_ms=1_000,
            poll_interval_ms=1,
        )
    )

    assert action_button is sentinel_button
    assert matched_card == {
        "text": "fixture-source-a.zip File contents may not be accessible",
        "key": "fixture-source-a.zip",
        "title": "fixture-source-a.zip",
        "subtitle": "File contents may not be accessible",
        "identity": "fixture-source-a.zip File contents may not be accessible",
    }
    assert captured_candidates == [[
        "fixture-source-a.zip",
        "fixture-source-a.zip File contents may not be accessible",
    ]]
    assert candidates == [
        "fixture-source-a.zip",
        "fixture-source-a.zip File contents may not be accessible",
    ]
    assert "File contents may not be accessible" not in candidates


def test_remove_project_source_non_exact_retries_with_anchored_candidates_only(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client.config.project_url = "https://chatgpt.com/g/g-p-69e2157ad4548191871f994c48de3aca/project"
    page = FakePage()

    options_button = FakeClickable()
    remove_button = FakeClickable()
    wait_calls: list[list[str]] = []
    source_absence_attempts = 0
    matched_card = {
        "text": "fixture-source-a.zip File contents may not be accessible",
        "key": "fixture-source-a.zip",
        "title": "fixture-source-a.zip",
        "subtitle": "File contents may not be accessible",
        "identity": "fixture-source-a.zip File contents may not be accessible",
    }

    async def fake_ensure_logged_in(*_args, **_kwargs):
        return None

    async def fake_goto(*_args, **_kwargs):
        return None

    async def fake_open_project_sources_tab(*_args, **_kwargs):
        return None

    async def fake_snapshot_project_source_cards(*_args, **_kwargs):
        return [
            matched_card,
            {
                "text": "fixture-source-b.zip File contents may not be accessible",
                "key": "fixture-source-b.zip",
                "title": "fixture-source-b.zip",
                "subtitle": "File contents may not be accessible",
                "identity": "fixture-source-b.zip File contents may not be accessible",
            },
        ]

    async def fake_wait_for_project_source_action_button(_page, source_names, *, exact: bool, **_kwargs):
        wait_calls.append(list(source_names))
        assert exact is False
        assert "File contents may not be accessible" not in source_names
        return options_button, matched_card, list(source_names)

    async def fake_wait_for_visible_locator(_page, _selectors, *, label: str, **_kwargs):
        if label == "project-source-remove-action":
            return remove_button
        if label == "project-source-remove-confirm":
            return None
        raise AssertionError(f"unexpected locator label: {label}")

    async def fake_wait_for_source_absence(*_args, **_kwargs):
        nonlocal source_absence_attempts
        source_absence_attempts += 1
        if source_absence_attempts == 1:
            raise client_module.ResponseTimeoutError("Timed out waiting for project source to disappear: fixture-source-a.zip")
        return None

    async def fake_safe_page_url(*_args, **_kwargs):
        return "https://chatgpt.com/g/g-p-69e2157ad4548191871f994c48de3aca/project?tab=sources"

    async def fake_project_source_is_stably_absent(*_args, **_kwargs):
        return True

    client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    client._goto = fake_goto  # type: ignore[method-assign]
    client._open_project_sources_tab = fake_open_project_sources_tab  # type: ignore[method-assign]
    client._snapshot_project_source_cards = fake_snapshot_project_source_cards  # type: ignore[method-assign]
    client._wait_for_project_source_action_button = fake_wait_for_project_source_action_button  # type: ignore[method-assign]
    client._wait_for_visible_locator = fake_wait_for_visible_locator  # type: ignore[method-assign]
    client._wait_for_source_absence = fake_wait_for_source_absence  # type: ignore[method-assign]
    client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    client._project_source_is_stably_absent = fake_project_source_is_stably_absent  # type: ignore[method-assign]

    result = asyncio.run(
        client._remove_project_source_operation(
            context=None,
            page=page,
            source_name="fixture-source-a.zip",
            exact=False,
            keep_open=False,
        )
    )

    assert result["ok"] is True
    assert wait_calls == [
        [
            "fixture-source-a.zip",
            "fixture-source-a.zip File contents may not be accessible",
        ],
        [
            "fixture-source-a.zip",
            "fixture-source-a.zip File contents may not be accessible",
        ],
    ]



def test_remove_project_source_tries_alternate_row_option_buttons_when_first_menu_does_not_open(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client.config.project_url = "https://chatgpt.com/g/g-p-69e2157ad4548191871f994c48de3aca/project"
    page = FakePage()

    wrong_options_button = FakeClickable()
    correct_options_button = FakeClickable()
    remove_button = FakeClickable()
    confirm_button = FakeClickable()
    matched_card = {
        "identity": "architecture-process_0.1.29.zip File contents may not be accessible",
        "title": "architecture-process_0.1.29.zip",
        "key": "architecture-process_0.1.29.zip",
        "text": "architecture-process_0.1.29.zip File contents may not be accessible",
    }

    async def fake_ensure_logged_in(*_args, **_kwargs):
        return None

    async def fake_goto(*_args, **_kwargs):
        return None

    async def fake_open_project_sources_tab(*_args, **_kwargs):
        return None

    async def fake_snapshot_project_source_cards(*_args, **_kwargs):
        return [] if confirm_button.click_count > 0 else [matched_card]

    async def fake_wait_for_project_source_action_button(_page, source_names, *, exact: bool, **_kwargs):
        return wrong_options_button, matched_card, list(source_names)

    async def fake_find_project_source_action_button_candidates_for_card(_page, _matched_card):
        return [wrong_options_button, correct_options_button]

    async def fake_wait_for_visible_locator(_page, _selectors, *, label: str, **_kwargs):
        if label == "project-source-remove-action":
            return remove_button if correct_options_button.click_count > 0 else None
        if label == "project-source-remove-confirm":
            return confirm_button
        raise AssertionError(f"unexpected locator label: {label}")

    async def fake_find_project_source_remove_action(_page):
        return remove_button if correct_options_button.click_count > 0 else None

    async def fake_wait_for_source_absence(*_args, **_kwargs):
        return None

    async def fake_safe_page_url(*_args, **_kwargs):
        return "https://chatgpt.com/g/g-p-69e2157ad4548191871f994c48de3aca/project?tab=sources"

    client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    client._goto = fake_goto  # type: ignore[method-assign]
    client._open_project_sources_tab = fake_open_project_sources_tab  # type: ignore[method-assign]
    client._snapshot_project_source_cards = fake_snapshot_project_source_cards  # type: ignore[method-assign]
    client._wait_for_project_source_action_button = fake_wait_for_project_source_action_button  # type: ignore[method-assign]
    client._find_project_source_action_button_candidates_for_card = fake_find_project_source_action_button_candidates_for_card  # type: ignore[method-assign]
    client._wait_for_visible_locator = fake_wait_for_visible_locator  # type: ignore[method-assign]
    client._find_project_source_remove_action = fake_find_project_source_remove_action  # type: ignore[method-assign]
    client._wait_for_source_absence = fake_wait_for_source_absence  # type: ignore[method-assign]
    client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]

    result = asyncio.run(
        client._remove_project_source_operation(
            context=None,
            page=page,
            source_name="architecture-process_0.1.29.zip",
            exact=False,
            keep_open=False,
        )
    )

    assert result["ok"] is True
    assert result["removed_via_ui"] is True
    assert wrong_options_button.click_count >= 1
    assert correct_options_button.click_count >= 1
    assert remove_button.click_count >= 1
    assert confirm_button.click_count >= 1

def test_remove_project_source_retries_options_click_with_force(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client.config.project_url = "https://chatgpt.com/g/g-p-69e2157ad4548191871f994c48de3aca/project"
    page = FakePage()

    options_button = FakeClickFailsThenForceSucceeds()
    remove_button = FakeClickable()
    confirm_button = FakeClickable()

    async def fake_ensure_logged_in(*_args, **_kwargs):
        return None

    async def fake_goto(*_args, **_kwargs):
        return None

    async def fake_open_project_sources_tab(*_args, **_kwargs):
        return None

    async def fake_snapshot_project_source_cards(*_args, **_kwargs):
        return [
            {
                "identity": "pasted.txt Document",
                "text": "pasted.txt Document",
                "key": "pasted.txt document",
            }
        ]

    async def fake_wait_for_project_source_action_button(*_args, **_kwargs):
        return options_button, {"identity": "pasted.txt Document"}, ["pasted.txt Document"]

    async def fake_wait_for_visible_locator(_page, _selectors, *, label: str, **_kwargs):
        if label == "project-source-remove-action":
            return remove_button
        if label == "project-source-remove-confirm":
            return confirm_button
        raise AssertionError(f"unexpected locator label: {label}")

    async def fake_wait_for_source_absence(*_args, **_kwargs):
        return None

    async def fake_safe_page_url(*_args, **_kwargs):
        return "https://chatgpt.com/g/g-p-69e2157ad4548191871f994c48de3aca/project?tab=sources"

    async def fake_project_source_is_stably_absent(*_args, **_kwargs):
        return True

    client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    client._goto = fake_goto  # type: ignore[method-assign]
    client._open_project_sources_tab = fake_open_project_sources_tab  # type: ignore[method-assign]
    client._snapshot_project_source_cards = fake_snapshot_project_source_cards  # type: ignore[method-assign]
    client._wait_for_project_source_action_button = fake_wait_for_project_source_action_button  # type: ignore[method-assign]
    client._wait_for_visible_locator = fake_wait_for_visible_locator  # type: ignore[method-assign]
    client._wait_for_source_absence = fake_wait_for_source_absence  # type: ignore[method-assign]
    client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    client._project_source_is_stably_absent = fake_project_source_is_stably_absent  # type: ignore[method-assign]

    result = asyncio.run(
        client._remove_project_source_operation(
            context=None,
            page=page,
            source_name="pasted.txt Document",
            exact=True,
            keep_open=False,
        )
    )

    assert result["ok"] is True
    assert options_button.click_count == 2
    assert options_button.force_click_count == 1
    assert remove_button.click_count == 1
    assert confirm_button.click_count == 1


def test_remove_project_source_retries_remove_action_when_first_click_has_no_effect(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client.config.project_url = "https://chatgpt.com/g/g-p-69e2157ad4548191871f994c48de3aca/project"
    page = FakePage()

    options_button = FakeClickable()
    remove_button = FakeClickable()
    confirm_button = FakeClickable()
    confirm_attempts = iter([None, confirm_button])
    source_absence_calls: list[int] = []

    async def fake_ensure_logged_in(*_args, **_kwargs):
        return None

    async def fake_goto(*_args, **_kwargs):
        return None

    async def fake_open_project_sources_tab(*_args, **_kwargs):
        return None

    async def fake_snapshot_project_source_cards(*_args, **_kwargs):
        return [
            {
                "identity": "pasted.txt Document",
                "text": "pasted.txt Document",
                "key": "pasted.txt document",
            }
        ]

    async def fake_wait_for_project_source_action_button(*_args, **_kwargs):
        return options_button, {"identity": "pasted.txt Document"}, ["pasted.txt Document"]

    async def fake_wait_for_visible_locator(_page, _selectors, *, label: str, **_kwargs):
        if label == "project-source-remove-action":
            return remove_button
        if label == "project-source-remove-confirm":
            return next(confirm_attempts)
        raise AssertionError(f"unexpected locator label: {label}")

    async def fake_wait_for_source_absence(*_args, **_kwargs):
        source_absence_calls.append(1)
        if len(source_absence_calls) == 1:
            raise client_module.ResponseTimeoutError("still present")
        return None

    async def fake_safe_page_url(*_args, **_kwargs):
        return "https://chatgpt.com/g/g-p-69e2157ad4548191871f994c48de3aca/project?tab=sources"

    async def fake_project_source_is_stably_absent(*_args, **_kwargs):
        return True

    client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    client._goto = fake_goto  # type: ignore[method-assign]
    client._open_project_sources_tab = fake_open_project_sources_tab  # type: ignore[method-assign]
    client._snapshot_project_source_cards = fake_snapshot_project_source_cards  # type: ignore[method-assign]
    client._wait_for_project_source_action_button = fake_wait_for_project_source_action_button  # type: ignore[method-assign]
    client._wait_for_visible_locator = fake_wait_for_visible_locator  # type: ignore[method-assign]
    client._wait_for_source_absence = fake_wait_for_source_absence  # type: ignore[method-assign]
    client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    client._project_source_is_stably_absent = fake_project_source_is_stably_absent  # type: ignore[method-assign]

    result = asyncio.run(
        client._remove_project_source_operation(
            context=None,
            page=page,
            source_name="pasted.txt Document",
            exact=True,
            keep_open=False,
        )
    )

    assert result["ok"] is True
    assert options_button.click_count == 2
    assert remove_button.click_count == 2
    assert confirm_button.click_count == 1
    assert len(source_absence_calls) == 2


def test_remove_project_source_aborts_when_retry_detects_collateral_removal(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client.config.project_url = "https://chatgpt.com/g/g-p-69e2157ad4548191871f994c48de3aca/project"
    page = FakePage()

    options_button = FakeClickable()
    remove_button = FakeClickable()
    matched_card = {
        "identity": "candlecast-src-0.19.5.82.1.zip",
        "title": "candlecast-src-0.19.5.82.1.zip",
        "key": "candlecast-src-0.19.5.82.1.zip",
        "text": "candlecast-src-0.19.5.82.1.zip File contents may not be accessible",
    }
    sibling_card = {
        "identity": "candlecast-src-0.19.5.82.zip",
        "title": "candlecast-src-0.19.5.82.zip",
        "key": "candlecast-src-0.19.5.82.zip",
        "text": "candlecast-src-0.19.5.82.zip File contents may not be accessible",
    }
    other_card = {
        "identity": "architecture-process_0.1.16.2.zip",
        "title": "architecture-process_0.1.16.2.zip",
        "key": "architecture-process_0.1.16.2.zip",
        "text": "architecture-process_0.1.16.2.zip File contents may not be accessible",
    }
    snapshots = iter([
        [matched_card, sibling_card, other_card],
        [matched_card, sibling_card, other_card],
        [matched_card, other_card],
    ])

    async def fake_ensure_logged_in(*_args, **_kwargs):
        return None

    async def fake_goto(*_args, **_kwargs):
        return None

    async def fake_open_project_sources_tab(*_args, **_kwargs):
        return None

    async def fake_snapshot_project_source_cards(*_args, **_kwargs):
        try:
            return next(snapshots)
        except StopIteration:
            return [matched_card, other_card]

    async def fake_wait_for_project_source_action_button(*_args, **_kwargs):
        return options_button, matched_card, [
            "candlecast-src-0.19.5.82.1.zip",
            "candlecast-src-0.19.5.82.1.zip File contents may not be accessible",
        ]

    async def fake_wait_for_visible_locator(_page, _selectors, *, label: str, **_kwargs):
        if label == "project-source-remove-action":
            return remove_button
        if label == "project-source-remove-confirm":
            return None
        raise AssertionError(f"unexpected locator label: {label}")

    async def fake_wait_for_source_absence(*_args, **_kwargs):
        raise client_module.ResponseTimeoutError("target still present")

    async def fake_safe_page_url(*_args, **_kwargs):
        return "https://chatgpt.com/g/g-p-69e2157ad4548191871f994c48de3aca/project?tab=sources"

    async def fake_project_source_is_stably_absent(*_args, **_kwargs):
        return True

    client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    client._goto = fake_goto  # type: ignore[method-assign]
    client._open_project_sources_tab = fake_open_project_sources_tab  # type: ignore[method-assign]
    client._snapshot_project_source_cards = fake_snapshot_project_source_cards  # type: ignore[method-assign]
    client._wait_for_project_source_action_button = fake_wait_for_project_source_action_button  # type: ignore[method-assign]
    client._wait_for_visible_locator = fake_wait_for_visible_locator  # type: ignore[method-assign]
    client._wait_for_source_absence = fake_wait_for_source_absence  # type: ignore[method-assign]
    client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    client._project_source_is_stably_absent = fake_project_source_is_stably_absent  # type: ignore[method-assign]

    with pytest.raises(client_module.ResponseTimeoutError, match="collateral_removed"):
        asyncio.run(
            client._remove_project_source_operation(
                context=None,
                page=page,
                source_name="candlecast-src-0.19.5.82.1.zip",
                exact=False,
                keep_open=False,
            )
        )


def test_remove_project_source_fails_when_target_removal_also_deletes_other_rows(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client.config.project_url = "https://chatgpt.com/g/g-p-69e2157ad4548191871f994c48de3aca/project"
    page = FakePage()

    options_button = FakeClickable()
    remove_button = FakeClickable()
    matched_card = {
        "identity": "candlecast-src-0.19.5.82.1.zip",
        "title": "candlecast-src-0.19.5.82.1.zip",
        "key": "candlecast-src-0.19.5.82.1.zip",
        "text": "candlecast-src-0.19.5.82.1.zip File contents may not be accessible",
    }
    sibling_card = {
        "identity": "candlecast-src-0.19.5.82.zip",
        "title": "candlecast-src-0.19.5.82.zip",
        "key": "candlecast-src-0.19.5.82.zip",
        "text": "candlecast-src-0.19.5.82.zip File contents may not be accessible",
    }
    other_card = {
        "identity": "architecture-process_0.1.16.2.zip",
        "title": "architecture-process_0.1.16.2.zip",
        "key": "architecture-process_0.1.16.2.zip",
        "text": "architecture-process_0.1.16.2.zip File contents may not be accessible",
    }
    snapshots = iter([
        [matched_card, sibling_card, other_card],
        [other_card],
    ])

    async def fake_ensure_logged_in(*_args, **_kwargs):
        return None

    async def fake_goto(*_args, **_kwargs):
        return None

    async def fake_open_project_sources_tab(*_args, **_kwargs):
        return None

    async def fake_snapshot_project_source_cards(*_args, **_kwargs):
        try:
            return next(snapshots)
        except StopIteration:
            return [other_card]

    async def fake_wait_for_project_source_action_button(*_args, **_kwargs):
        return options_button, matched_card, [
            "candlecast-src-0.19.5.82.1.zip",
            "candlecast-src-0.19.5.82.1.zip File contents may not be accessible",
        ]

    async def fake_wait_for_visible_locator(_page, _selectors, *, label: str, **_kwargs):
        if label == "project-source-remove-action":
            return remove_button
        if label == "project-source-remove-confirm":
            return None
        raise AssertionError(f"unexpected locator label: {label}")

    async def fake_wait_for_source_absence(*_args, **_kwargs):
        return None

    async def fake_safe_page_url(*_args, **_kwargs):
        return "https://chatgpt.com/g/g-p-69e2157ad4548191871f994c48de3aca/project?tab=sources"

    async def fake_project_source_is_stably_absent(*_args, **_kwargs):
        return True

    client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    client._goto = fake_goto  # type: ignore[method-assign]
    client._open_project_sources_tab = fake_open_project_sources_tab  # type: ignore[method-assign]
    client._snapshot_project_source_cards = fake_snapshot_project_source_cards  # type: ignore[method-assign]
    client._wait_for_project_source_action_button = fake_wait_for_project_source_action_button  # type: ignore[method-assign]
    client._wait_for_visible_locator = fake_wait_for_visible_locator  # type: ignore[method-assign]
    client._wait_for_source_absence = fake_wait_for_source_absence  # type: ignore[method-assign]
    client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    client._project_source_is_stably_absent = fake_project_source_is_stably_absent  # type: ignore[method-assign]

    with pytest.raises(client_module.ResponseTimeoutError, match="deleted additional rows"):
        asyncio.run(
            client._remove_project_source_operation(
                context=None,
                page=page,
                source_name="candlecast-src-0.19.5.82.1.zip",
                exact=False,
                keep_open=False,
            )
        )


def test_remove_project_source_succeeds_when_removal_is_immediate_without_confirm(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client.config.project_url = "https://chatgpt.com/g/g-p-69e2157ad4548191871f994c48de3aca/project"
    page = FakePage()

    options_button = FakeClickable()
    remove_button = FakeClickable()
    source_absence_calls: list[int] = []

    async def fake_ensure_logged_in(*_args, **_kwargs):
        return None

    async def fake_goto(*_args, **_kwargs):
        return None

    async def fake_open_project_sources_tab(*_args, **_kwargs):
        return None

    async def fake_snapshot_project_source_cards(*_args, **_kwargs):
        return [
            {
                "identity": "pasted.txt Document",
                "text": "pasted.txt Document",
                "key": "pasted.txt document",
            }
        ]

    async def fake_wait_for_project_source_action_button(*_args, **_kwargs):
        return options_button, {"identity": "pasted.txt Document"}, ["pasted.txt Document"]

    async def fake_wait_for_visible_locator(_page, _selectors, *, label: str, **_kwargs):
        if label == "project-source-remove-action":
            return remove_button
        if label == "project-source-remove-confirm":
            return None
        raise AssertionError(f"unexpected locator label: {label}")

    async def fake_wait_for_source_absence(*_args, **_kwargs):
        source_absence_calls.append(1)
        return None

    async def fake_safe_page_url(*_args, **_kwargs):
        return "https://chatgpt.com/g/g-p-69e2157ad4548191871f994c48de3aca/project?tab=sources"

    async def fake_project_source_is_stably_absent(*_args, **_kwargs):
        return True

    client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    client._goto = fake_goto  # type: ignore[method-assign]
    client._open_project_sources_tab = fake_open_project_sources_tab  # type: ignore[method-assign]
    client._snapshot_project_source_cards = fake_snapshot_project_source_cards  # type: ignore[method-assign]
    client._wait_for_project_source_action_button = fake_wait_for_project_source_action_button  # type: ignore[method-assign]
    client._wait_for_visible_locator = fake_wait_for_visible_locator  # type: ignore[method-assign]
    client._wait_for_source_absence = fake_wait_for_source_absence  # type: ignore[method-assign]
    client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]
    client._project_source_is_stably_absent = fake_project_source_is_stably_absent  # type: ignore[method-assign]

    result = asyncio.run(
        client._remove_project_source_operation(
            context=None,
            page=page,
            source_name="pasted.txt Document",
            exact=True,
            keep_open=False,
        )
    )

    assert result["ok"] is True
    assert options_button.click_count == 1
    assert remove_button.click_count == 1
    assert len(source_absence_calls) == 1

def test_remove_project_source_returns_idempotent_success_when_source_is_already_absent(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client.config.project_url = "https://chatgpt.com/g/g-p-69e2157ad4548191871f994c48de3aca/project"
    page = FakePage()

    async def fake_ensure_logged_in(*_args, **_kwargs):
        return None

    async def fake_goto(*_args, **_kwargs):
        return None

    async def fake_open_project_sources_tab(*_args, **_kwargs):
        return None

    async def fake_snapshot_project_source_cards(*_args, **_kwargs):
        return []

    async def fake_wait_for_project_source_action_button(*_args, **_kwargs):
        return None, None, ["pasted.txt Document"]

    async def fake_project_source_is_stably_absent(*_args, **_kwargs):
        return True

    async def fake_safe_page_url(*_args, **_kwargs):
        return "https://chatgpt.com/g/g-p-69e2157ad4548191871f994c48de3aca/project?tab=sources"

    client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    client._goto = fake_goto  # type: ignore[method-assign]
    client._open_project_sources_tab = fake_open_project_sources_tab  # type: ignore[method-assign]
    client._snapshot_project_source_cards = fake_snapshot_project_source_cards  # type: ignore[method-assign]
    client._wait_for_project_source_action_button = fake_wait_for_project_source_action_button  # type: ignore[method-assign]
    client._project_source_is_stably_absent = fake_project_source_is_stably_absent  # type: ignore[method-assign]
    client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]

    result = asyncio.run(
        client._remove_project_source_operation(
            context=None,
            page=page,
            source_name="pasted.txt Document",
            exact=True,
            keep_open=False,
        )
    )

    assert result["ok"] is True
    assert result["already_absent"] is True
    assert result["removed_via_ui"] is False
    assert result["source_match"] == "pasted.txt Document"
    assert result["source_identity_used"] == "pasted.txt Document"


def test_remove_project_source_returns_idempotent_success_when_target_absent_but_other_sources_remain(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client.config.project_url = "https://chatgpt.com/g/g-p-69e2157ad4548191871f994c48de3aca/project"
    page = FakePage()

    async def fake_ensure_logged_in(*_args, **_kwargs):
        return None

    async def fake_goto(*_args, **_kwargs):
        return None

    async def fake_open_project_sources_tab(*_args, **_kwargs):
        return None

    async def fake_snapshot_project_source_cards(*_args, **_kwargs):
        return [
            {
                "text": "architecture-process_0.1.16.2.zip File contents may not be accessible",
                "key": "architecture-process_0.1.16.2.zip",
                "title": "architecture-process_0.1.16.2.zip",
                "subtitle": "File contents may not be accessible",
                "identity": "architecture-process_0.1.16.2.zip File contents may not be accessible",
            }
        ]

    async def fake_wait_for_project_source_action_button(*_args, **_kwargs):
        return None, None, ["candlecast-src-0.19.5.82.1.zip"]

    async def fake_find_project_source_action_button(*_args, **_kwargs):
        return None

    async def fake_find_project_source_container(*_args, **_kwargs):
        return None

    async def fake_project_sources_empty_state_visible(*_args, **_kwargs):
        return False

    async def fake_safe_page_url(*_args, **_kwargs):
        return "https://chatgpt.com/g/g-p-69e2157ad4548191871f994c48de3aca/project?tab=sources"

    client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    client._goto = fake_goto  # type: ignore[method-assign]
    client._open_project_sources_tab = fake_open_project_sources_tab  # type: ignore[method-assign]
    client._snapshot_project_source_cards = fake_snapshot_project_source_cards  # type: ignore[method-assign]
    client._wait_for_project_source_action_button = fake_wait_for_project_source_action_button  # type: ignore[method-assign]
    client._find_project_source_action_button = fake_find_project_source_action_button  # type: ignore[method-assign]
    client._find_project_source_container = fake_find_project_source_container  # type: ignore[method-assign]
    client._project_sources_empty_state_visible = fake_project_sources_empty_state_visible  # type: ignore[method-assign]
    client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]

    result = asyncio.run(
        client._remove_project_source_operation(
            context=None,
            page=page,
            source_name="candlecast-src-0.19.5.82.1.zip",
            exact=False,
            keep_open=False,
        )
    )

    assert result["ok"] is True
    assert result["already_absent"] is True
    assert result["removed_via_ui"] is False
    assert result["source_match"] == "candlecast-src-0.19.5.82.1.zip"
    assert result["source_identity_used"] == "candlecast-src-0.19.5.82.1.zip"


def test_respect_context_spacing_waits_between_browser_context_launches(tmp_path: Path, monkeypatch) -> None:
    client = _make_client(tmp_path)
    client.config.min_context_spacing_seconds = 5.0
    client_module._PROFILE_LAST_CONTEXT_CLOSED_AT[client._profile_key] = 100.0

    monkeypatch.setattr(client_module.time, "monotonic", lambda: 103.0)

    slept: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(client_module.asyncio, "sleep", fake_sleep)

    asyncio.run(client._respect_context_spacing())

    assert slept == [2.0]


def test_note_conversation_history_rate_limit_persists_cooldown_file(tmp_path: Path, monkeypatch) -> None:
    client = _make_client(tmp_path)
    client.config.conversation_history_rate_limit_cooldown_seconds = 30.0
    monkeypatch.setattr(client_module.time, "time", lambda: 1_000.0)

    client._note_conversation_history_rate_limit(
        trigger="response",
        url="https://chatgpt.com/backend-api/conversations?offset=0",
        status=429,
    )

    assert client._rate_limit_cooldown_path.exists() is True
    assert float(client._rate_limit_cooldown_path.read_text(encoding="utf-8")) == pytest.approx(1_030.0)




def test_backend_api_403_does_not_persist_cooldown_in_release_live_fail_fast_mode(tmp_path: Path, monkeypatch) -> None:
    client = _make_client(tmp_path)
    client.config.fail_fast_on_challenge = True
    client.config.conversation_history_rate_limit_cooldown_seconds = 180.0
    monkeypatch.setattr(client_module.time, "time", lambda: 1_000.0)

    client._note_backend_api_guardrail(
        trigger="response",
        url="https://chatgpt.com/backend-api/me",
        status=403,
    )

    telemetry = client._rate_limit_telemetry_snapshot()
    assert telemetry["backend_api_guardrail_seen"] is True
    assert client._rate_limit_cooldown_path.exists() is False


def test_midrun_target_closed_after_backend_403_maps_to_standard_profile_challenged(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client.config.fail_fast_on_challenge = True
    client._note_backend_api_guardrail(
        trigger="response",
        url="https://chatgpt.com/backend-api/me",
        status=403,
    )

    class ClosedPage:
        url = "https://chatgpt.com/"

        async def title(self) -> str:
            raise RuntimeError("Target page, context or browser has been closed")

        async def evaluate(self, _script: str):
            raise RuntimeError("Target page, context or browser has been closed")

    class TargetClosedError(RuntimeError):
        pass

    with pytest.raises(AuthChallengeRequiredError) as raised:
        asyncio.run(
            client._raise_fail_fast_midrun_challenge_if_configured(
                ClosedPage(),
                stage="response-wait-page-closed",
                exc=TargetClosedError("Page.wait_for_timeout: Target page, context or browser has been closed"),
            )
        )

    assert raised.value.challenge_type == "docker_standard_profile_challenged"
    assert "Cloudflare/backend-403 guardrail" in str(raised.value)


def test_midrun_root_after_backend_403_maps_to_standard_profile_challenged(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client.config.fail_fast_on_challenge = True
    client._note_backend_api_guardrail(
        trigger="response",
        url="https://chatgpt.com/backend-api/gizmos/example",
        status=403,
    )

    class RootPage:
        url = "https://chatgpt.com/"

        async def title(self) -> str:
            return "ChatGPT"

        async def evaluate(self, _script: str):
            return ""

    with pytest.raises(AuthChallengeRequiredError) as raised:
        asyncio.run(
            client._raise_fail_fast_midrun_challenge_if_configured(
                RootPage(),
                stage="response-wait-poll",
            )
        )

    assert raised.value.challenge_type == "docker_standard_profile_challenged"

def test_respect_rate_limit_cooldown_waits_for_persisted_deadline(tmp_path: Path, monkeypatch) -> None:
    client = _make_client(tmp_path)
    client._rate_limit_cooldown_path.parent.mkdir(parents=True, exist_ok=True)
    client._rate_limit_cooldown_path.write_text("1010.0", encoding="utf-8")
    monkeypatch.setattr(client_module.time, "time", lambda: 1_000.0)

    slept: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(client_module.asyncio, "sleep", fake_sleep)

    asyncio.run(client._respect_rate_limit_cooldown())

    assert slept == [10.0]


def test_rate_limit_modal_clear_can_skip_history_cooldown_for_non_history_operation(tmp_path: Path, monkeypatch) -> None:
    client = _make_client(tmp_path)
    client.config.conversation_history_rate_limit_cooldown_seconds = 120.0
    monkeypatch.setattr(client_module.time, "time", lambda: 1_000.0)

    class Page:
        url = "https://chatgpt.com/g/g-p-123/project?tab=sources"

        async def wait_for_timeout(self, _ms: int) -> None:
            return None

    modal_remaining = {"count": 1}
    ack = object()

    async def fake_find_visible_locator(_page, _selectors, *, label: str):
        if label.endswith("-rate-limit-modal"):
            if modal_remaining["count"] > 0:
                modal_remaining["count"] -= 1
                return object()
            return None
        if label.endswith("-rate-limit-ack"):
            return ack
        return None

    async def fake_click_locator_with_fallback(*_args, **_kwargs) -> None:
        return None

    async def fail_if_history_cooldown_waits() -> None:
        raise AssertionError("non-history Project Source verification must not wait on conversation-history cooldown")

    client._find_visible_locator = fake_find_visible_locator  # type: ignore[method-assign]
    client._click_locator_with_fallback = fake_click_locator_with_fallback  # type: ignore[method-assign]
    client._respect_rate_limit_cooldown = fail_if_history_cooldown_waits  # type: ignore[method-assign]

    saw_modal = asyncio.run(
        client._wait_for_rate_limit_modal_to_clear(
            Page(),
            label="project-source-add-persistence-refresh",
            respect_history_rate_limit_cooldown=False,
        )
    )

    telemetry = client._rate_limit_telemetry_snapshot()
    assert saw_modal is True
    assert telemetry["cooldown_wait_count"] == 0
    assert any(event.get("kind") == "cooldown_wait_skipped" for event in telemetry["service_rate_limit_events"])




def test_rate_limit_modal_ack_waits_one_minute_and_consumes_cooldown(tmp_path: Path, monkeypatch) -> None:
    client = _make_client(tmp_path)
    client.config.conversation_history_rate_limit_cooldown_seconds = 180.0
    client.config.rate_limit_modal_ack_wait_seconds = 60.0
    monkeypatch.setattr(client_module.time, "time", lambda: 1_000.0)

    class Page:
        url = "https://chatgpt.com/g/g-p-123/project"

        async def wait_for_timeout(self, _ms: int) -> None:
            return None

    modal_remaining = {"count": 1}
    ack = object()
    clicked: list[str] = []
    slept: list[float] = []

    async def fake_find_visible_locator(_page, _selectors, *, label: str):
        if label.endswith("-rate-limit-modal"):
            if modal_remaining["count"] > 0:
                modal_remaining["count"] -= 1
                return object()
            return None
        if label.endswith("-rate-limit-ack"):
            return ack
        return None

    async def fake_click_locator_with_fallback(_locator, *, label: str, **_kwargs) -> None:
        clicked.append(label)

    async def fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    client._find_visible_locator = fake_find_visible_locator  # type: ignore[method-assign]
    client._click_locator_with_fallback = fake_click_locator_with_fallback  # type: ignore[method-assign]
    monkeypatch.setattr(client_module.asyncio, "sleep", fake_sleep)

    saw_modal = asyncio.run(
        client._wait_for_rate_limit_modal_to_clear(
            Page(),
            label="ask-live-rate-limit-proof",
            timeout_ms=5_000,
        )
    )

    telemetry = client._rate_limit_telemetry_snapshot()
    events = telemetry["service_rate_limit_events"]
    assert saw_modal is True
    assert clicked == ["ask-live-rate-limit-proof-rate-limit-ack"]
    assert slept == [60.0]
    assert float(client._rate_limit_cooldown_path.read_text(encoding="utf-8")) == pytest.approx(1_000.0)
    assert any(event.get("kind") == "modal_acknowledged" for event in events)
    assert any(event.get("kind") == "modal_ack_wait" for event in events)
    assert any(event.get("kind") == "cooldown_wait_satisfied_by_modal_ack_wait" for event in events)

class _ProjectCreateButton:
    def __init__(self, enabled_sequence):
        self.enabled_sequence = list(enabled_sequence)
        self.fill_values = []
        self.press_values = []
        self.click_count = 0

    async def is_enabled(self):
        if self.enabled_sequence:
            return self.enabled_sequence.pop(0)
        return False

    async def get_attribute(self, _name):
        return None

    async def evaluate(self, _script, *args):
        if args:
            self.fill_values.append(args[0])
        return {"disabled": False, "ariaDisabled": None, "visuallyDisabled": None, "text": "Create"}

    async def click(self, *args, **kwargs):
        self.click_count += 1

    async def fill(self, value):
        self.fill_values.append(value)

    async def press(self, value, *args, **kwargs):
        self.press_values.append(value)

    async def scroll_into_view_if_needed(self, *args, **kwargs):
        return None


class _ProjectCreateInput(_ProjectCreateButton):
    async def evaluate(self, _script, *args):
        if args:
            self.fill_values.append(args[0])
            return None
        return self.fill_values[-1] if self.fill_values else ""


def test_project_create_disabled_submit_recovers_after_rate_limit_modal_ack(tmp_path: Path):
    client = _make_client(tmp_path)
    page = FakePage()
    input_locator = _ProjectCreateInput([True])
    submit_locator = _ProjectCreateButton([False])
    calls = []
    enabled_results = [False, True]

    async def fake_wait_enabled(_locator, *, timeout_ms: int = 5_000):
        return enabled_results.pop(0)

    async def fake_wait_rate_limit(_page, *, label: str, **_kwargs):
        calls.append(label)
        return True

    async def fake_wait_for_visible_locator(_page, _selectors, *, label: str, **_kwargs):
        assert label == "project-create-submit-recovery-1-button"
        return submit_locator

    logs = []

    async def fake_log_disabled_state(_page, _input, _button, *, label: str):
        logs.append(label)

    client._wait_for_enabled_locator = fake_wait_enabled  # type: ignore[method-assign]
    client._wait_for_rate_limit_modal_to_clear = fake_wait_rate_limit  # type: ignore[method-assign]
    client._wait_for_visible_locator = fake_wait_for_visible_locator  # type: ignore[method-assign]
    client._log_project_create_disabled_state = fake_log_disabled_state  # type: ignore[method-assign]

    recovered = asyncio.run(
        client._recover_project_create_submit_enabled(
            page,
            input_locator,
            submit_locator,
            name="itest-promptbranch-v0-1-84-3",
        )
    )

    assert recovered is submit_locator
    assert calls == ["project-create-submit-recovery-1-rate-limit"]
    assert "project-create-submit-pre-recovery" in logs
    assert input_locator.fill_values[-1] == "itest-promptbranch-v0-1-84-3"
    assert "Tab" in input_locator.press_values


def test_project_create_disabled_submit_fails_after_bounded_recovery(tmp_path: Path):
    client = _make_client(tmp_path)
    client.config.project_create_disabled_recovery_attempts = 1
    page = FakePage()
    input_locator = _ProjectCreateInput([True])
    submit_locator = _ProjectCreateButton([False])

    async def fake_wait_enabled(_locator, *, timeout_ms: int = 5_000):
        return False

    async def fake_wait_rate_limit(_page, *, label: str, **_kwargs):
        return False

    async def fake_wait_for_visible_locator(_page, _selectors, *, label: str, **_kwargs):
        return submit_locator

    async def fake_log_disabled_state(_page, _input, _button, *, label: str):
        return None

    client._wait_for_enabled_locator = fake_wait_enabled  # type: ignore[method-assign]
    client._wait_for_rate_limit_modal_to_clear = fake_wait_rate_limit  # type: ignore[method-assign]
    client._wait_for_visible_locator = fake_wait_for_visible_locator  # type: ignore[method-assign]
    client._log_project_create_disabled_state = fake_log_disabled_state  # type: ignore[method-assign]

    with pytest.raises(client_module.ResponseTimeoutError, match="bounded recovery"):
        asyncio.run(
            client._recover_project_create_submit_enabled(
                page,
                input_locator,
                submit_locator,
                name="itest-promptbranch-v0-1-84-3",
            )
        )


class _FakeInteractiveStdin:
    def isatty(self) -> bool:
        return True


class _FakeNonInteractiveStdin:
    def isatty(self) -> bool:
        return False


def test_pause_for_keep_open_skips_when_stdin_is_not_interactive(tmp_path: Path, monkeypatch) -> None:
    client = _make_client(tmp_path)

    called = False

    async def fake_to_thread(*_args, **_kwargs):
        nonlocal called
        called = True
        return None

    monkeypatch.setattr(client_module.sys, "stdin", _FakeNonInteractiveStdin())
    monkeypatch.setattr(client_module.asyncio, "to_thread", fake_to_thread)

    asyncio.run(client._pause_for_keep_open("Project already exists. Press Enter to close the browser... "))

    assert called is False


def test_pause_for_keep_open_waits_when_stdin_is_interactive(tmp_path: Path, monkeypatch) -> None:
    client = _make_client(tmp_path)

    prompts: list[str] = []

    async def fake_to_thread(func, prompt: str):
        prompts.append(prompt)
        return None

    monkeypatch.setattr(client_module.sys, "stdin", _FakeInteractiveStdin())
    monkeypatch.setattr(client_module.asyncio, "to_thread", fake_to_thread)

    asyncio.run(client._pause_for_keep_open("Project already exists. Press Enter to close the browser... "))

    assert prompts == ["Project already exists. Press Enter to close the browser... "]


def test_ensure_project_existing_skips_keep_open_prompt_without_interactive_stdin(tmp_path: Path, monkeypatch) -> None:
    client = _make_client(tmp_path)
    client.config.headless = False
    page = FakePage()

    async def fake_ensure_logged_in(*_args, **_kwargs) -> None:
        return None

    async def fake_resolve_projects_by_name(*_args, **_kwargs):
        return {
            "match_count": 1,
            "project_url": "https://chatgpt.com/g/g-p-123/project",
            "matches": [{"name": "demo-project", "url": "https://chatgpt.com/g/g-p-123/project"}],
            "matched_by": "exact_name",
            "error": None,
        }

    async def fake_safe_page_url(*_args, **_kwargs) -> str:
        return "https://chatgpt.com/"

    called = False

    async def fake_to_thread(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("interactive input should not run without a tty")

    client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    client._resolve_projects_by_name = fake_resolve_projects_by_name  # type: ignore[method-assign]
    client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]

    monkeypatch.setattr(client_module.sys, "stdin", _FakeNonInteractiveStdin())
    monkeypatch.setattr(client_module.asyncio, "to_thread", fake_to_thread)

    result = asyncio.run(
        client._ensure_project_operation(
            context=None,
            page=page,
            name="demo-project",
            icon=None,
            color=None,
            memory_mode="default",
            keep_open=True,
        )
    )

    assert result["ok"] is True
    assert result["created"] is False
    assert result["project_url"] == "https://chatgpt.com/g/g-p-123/project"
    assert called is False

def test_remove_project_source_uses_dom_fallback_when_selector_menu_action_missing(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client.config.project_url = "https://chatgpt.com/g/g-p-69e2157ad4548191871f994c48de3aca/project"
    page = FakePage()

    options_button = FakeClickable()
    fallback_remove_button = FakeClickable()
    snapshots = [
        [{"identity": "architecture-process_0.1.29.zip File contents may not be accessible", "title": "architecture-process_0.1.29.zip", "text": "architecture-process_0.1.29.zip File contents may not be accessible"}],
        [{"identity": "architecture-process_0.1.29.zip File contents may not be accessible", "title": "architecture-process_0.1.29.zip", "text": "architecture-process_0.1.29.zip File contents may not be accessible"}],
        [],
    ]

    async def fake_ensure_logged_in(*_args, **_kwargs):
        return None

    async def fake_goto(*_args, **_kwargs):
        return None

    async def fake_open_project_sources_tab(*_args, **_kwargs):
        return None

    async def fake_snapshot_project_source_cards(*_args, **_kwargs):
        if snapshots:
            return snapshots.pop(0)
        return []

    async def fake_wait_for_project_source_action_button(_page, source_names, *, exact: bool, **_kwargs):
        return options_button, {"identity": "architecture-process_0.1.29.zip", "title": "architecture-process_0.1.29.zip"}, list(source_names)

    async def fake_wait_for_visible_locator(_page, _selectors, *, label: str, **_kwargs):
        if label == "project-source-remove-action":
            return None
        if label == "project-source-remove-confirm":
            return None
        raise AssertionError(f"unexpected locator label: {label}")

    async def fake_find_project_source_remove_action(_page):
        return fallback_remove_button

    async def fake_wait_for_source_absence(*_args, **_kwargs):
        return None

    async def fake_safe_page_url(*_args, **_kwargs):
        return "https://chatgpt.com/g/g-p-69e2157ad4548191871f994c48de3aca/project?tab=sources"

    client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    client._goto = fake_goto  # type: ignore[method-assign]
    client._open_project_sources_tab = fake_open_project_sources_tab  # type: ignore[method-assign]
    client._snapshot_project_source_cards = fake_snapshot_project_source_cards  # type: ignore[method-assign]
    client._wait_for_project_source_action_button = fake_wait_for_project_source_action_button  # type: ignore[method-assign]
    client._wait_for_visible_locator = fake_wait_for_visible_locator  # type: ignore[method-assign]
    client._find_project_source_remove_action = fake_find_project_source_remove_action  # type: ignore[method-assign]
    client._wait_for_source_absence = fake_wait_for_source_absence  # type: ignore[method-assign]
    client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]

    result = asyncio.run(
        client._remove_project_source_operation(
            context=None,
            page=page,
            source_name="architecture-process_0.1.29.zip",
            exact=False,
            keep_open=False,
        )
    )

    assert result["ok"] is True
    assert result["removed_via_ui"] is True
    assert options_button.click_count >= 1
    assert fallback_remove_button.click_count >= 1


def test_remove_project_source_uses_direct_card_remove_button_before_options_menu(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client.config.project_url = "https://chatgpt.com/g/g-p-69e2157ad4548191871f994c48de3aca/project"
    page = FakePage()

    options_button = FakeClickable()
    direct_remove_button = FakeClickable()
    confirm_button = FakeClickable()
    matched_card = {
        "identity": "architecture-process_0.1.29.zip File contents may not be accessible",
        "title": "architecture-process_0.1.29.zip",
        "key": "architecture-process_0.1.29.zip",
        "text": "architecture-process_0.1.29.zip File contents may not be accessible",
    }

    async def fake_ensure_logged_in(*_args, **_kwargs):
        return None

    async def fake_goto(*_args, **_kwargs):
        return None

    async def fake_open_project_sources_tab(*_args, **_kwargs):
        return None

    async def fake_snapshot_project_source_cards(*_args, **_kwargs):
        return [] if confirm_button.click_count > 0 else [matched_card]

    async def fake_wait_for_project_source_action_button(_page, source_names, *, exact: bool, **_kwargs):
        return options_button, matched_card, list(source_names)

    async def fake_find_project_source_direct_remove_action_for_card(_page, _matched_card):
        return direct_remove_button

    async def fake_wait_for_visible_locator(_page, _selectors, *, label: str, **_kwargs):
        if label == "project-source-remove-confirm":
            return confirm_button
        if label == "project-source-remove-action":
            raise AssertionError("menu action lookup should not be needed when direct card remove button exists")
        raise AssertionError(f"unexpected locator label: {label}")

    async def fake_wait_for_source_absence(*_args, **_kwargs):
        return None

    async def fake_safe_page_url(*_args, **_kwargs):
        return "https://chatgpt.com/g/g-p-69e2157ad4548191871f994c48de3aca/project?tab=sources"

    client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    client._goto = fake_goto  # type: ignore[method-assign]
    client._open_project_sources_tab = fake_open_project_sources_tab  # type: ignore[method-assign]
    client._snapshot_project_source_cards = fake_snapshot_project_source_cards  # type: ignore[method-assign]
    client._wait_for_project_source_action_button = fake_wait_for_project_source_action_button  # type: ignore[method-assign]
    client._find_project_source_direct_remove_action_for_card = fake_find_project_source_direct_remove_action_for_card  # type: ignore[method-assign]
    client._wait_for_visible_locator = fake_wait_for_visible_locator  # type: ignore[method-assign]
    client._wait_for_source_absence = fake_wait_for_source_absence  # type: ignore[method-assign]
    client._safe_page_url = fake_safe_page_url  # type: ignore[method-assign]

    result = asyncio.run(
        client._remove_project_source_operation(
            context=None,
            page=page,
            source_name="architecture-process_0.1.29.zip",
            exact=False,
            keep_open=False,
        )
    )

    assert result["ok"] is True
    assert result["removed_via_ui"] is True
    assert direct_remove_button.click_count == 1
    assert confirm_button.click_count == 1
    assert options_button.click_count == 0


def test_note_backend_api_guardrail_persists_cooldown_file(tmp_path: Path, monkeypatch) -> None:
    client = _make_client(tmp_path)
    monkeypatch.setattr(client_module.time, "time", lambda: 2_000.0)

    client._note_backend_api_guardrail(
        trigger="debug_response",
        url="https://chatgpt.com/backend-api/conversations?offset=0&limit=1",
        status=403,
        retry_after_seconds=45.0,
    )

    assert client._rate_limit_cooldown_path.exists() is True
    assert float(client._rate_limit_cooldown_path.read_text(encoding="utf-8")) == pytest.approx(2_045.0)
    telemetry = client._rate_limit_telemetry_snapshot()
    assert telemetry["backend_api_guardrail_seen"] is True


def test_backend_api_url_redaction_keeps_path_and_redacts_query(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    redacted = client._redact_backend_api_url(
        "https://chatgpt.com/backend-api/conversations?offset=0&limit=1&token=secret"
    )

    assert redacted["path"] == "/backend-api/conversations"
    assert redacted["query_keys"] == ["limit", "offset", "token"]
    assert "secret" not in redacted["redacted_url"]
    assert "token=<redacted>" in redacted["redacted_url"]


def test_project_page_details_selectors_include_generic_more_menu_fallbacks() -> None:
    from promptbranch_browser_auth.client import PROJECT_PAGE_DETAILS_MENU_SELECTORS

    joined = "\n".join(PROJECT_PAGE_DETAILS_MENU_SELECTORS).lower()

    assert 'project details' in joined
    assert 'project options' in joined
    assert 'more options' in joined
    assert 'aria-label="more"' in joined


def test_find_project_sidebar_container_includes_name_only_non_anchor_candidates(tmp_path: Path) -> None:
    client = _make_client(tmp_path)

    class _Element:
        pass

    expected = _Element()

    class _Handle:
        def as_element(self):
            return expected

    class _Page:
        def __init__(self) -> None:
            self.script = ""
            self.args = None

        async def evaluate_handle(self, script: str, args=None):
            self.script = script
            self.args = args
            return _Handle()

    page = _Page()
    result = asyncio.run(
        client._find_project_sidebar_container(
            page,
            project_url="https://chatgpt.com/g/g-p-demo-itest-leak/project",
            project_name="itest-leak",
        )
    )

    assert result is expected
    assert page.args["projectId"] == "g-p-demo"
    assert page.args["projectName"] == "itest-leak"
    assert "aside [role=\"button\"]" in page.script
    assert "[role=\"menuitem\"]" in page.script
    assert "[data-sidebar-item=\"true\"]" in page.script


def test_response_wait_ignores_backend_403_recorded_before_confirmed_submit(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client.config.fail_fast_on_challenge = True
    client._note_backend_api_guardrail(
        trigger="response",
        url="https://chatgpt.com/backend-api/files/download/file_old?inline=false",
        status=403,
    )
    response_context = {
        "submit_confirmed": True,
        "submit_confirmed_monotonic": client._rate_limit_events[-1]["monotonic_time"] + 0.001,
        "guardrail_event_cursor": len(client._rate_limit_events),
        "guardrail_scope_conversation_url": "https://chatgpt.com/g/g-p-demo/c/conversation-current",
    }

    class ConversationPage:
        url = "https://chatgpt.com/g/g-p-demo/c/conversation-current"

        async def title(self) -> str:
            return "Promptbranch"

        async def evaluate(self, _script: str):
            return ""

    asyncio.run(
        client._raise_fail_fast_midrun_challenge_if_configured(
            ConversationPage(),
            stage="response-wait-poll",
            response_context=response_context,
        )
    )


def test_response_wait_ignores_unrelated_post_submit_file_download_403(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client.config.fail_fast_on_challenge = True
    response_context = {
        "submit_confirmed": True,
        "submit_confirmed_monotonic": 0.0,
        "guardrail_event_cursor": len(client._rate_limit_events),
        "guardrail_scope_conversation_url": "https://chatgpt.com/g/g-p-demo/c/conversation-current",
    }
    client._note_backend_api_guardrail(
        trigger="response",
        url="https://chatgpt.com/backend-api/files/download/file_background?inline=false",
        status=403,
    )

    class ConversationPage:
        url = "https://chatgpt.com/g/g-p-demo/c/conversation-current"

        async def title(self) -> str:
            return "Promptbranch"

        async def evaluate(self, _script: str):
            return ""

    asyncio.run(
        client._raise_fail_fast_midrun_challenge_if_configured(
            ConversationPage(),
            stage="response-wait-poll",
            response_context=response_context,
        )
    )


def test_response_wait_rejects_post_submit_conversation_403(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client.config.fail_fast_on_challenge = True
    response_context = {
        "submit_confirmed": True,
        "submit_confirmed_monotonic": 0.0,
        "guardrail_event_cursor": len(client._rate_limit_events),
        "guardrail_scope_conversation_url": "https://chatgpt.com/g/g-p-demo/c/conversation-current",
    }
    client._note_backend_api_guardrail(
        trigger="response",
        url="https://chatgpt.com/backend-api/f/conversation",
        status=403,
    )

    class ConversationPage:
        url = "https://chatgpt.com/g/g-p-demo/c/conversation-current"

        async def title(self) -> str:
            return "Promptbranch"

        async def evaluate(self, _script: str):
            return "visible conversation"

    with pytest.raises(AuthChallengeRequiredError) as raised:
        asyncio.run(
            client._raise_fail_fast_midrun_challenge_if_configured(
                ConversationPage(),
                stage="response-wait-poll",
                response_context=response_context,
            )
        )

    assert raised.value.challenge_type == "docker_standard_profile_challenged"
    assert "current operation" in str(raised.value)
