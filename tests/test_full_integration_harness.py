from __future__ import annotations

import pytest

from promptbranch_full_integration_test import make_parser, resolve_step_selection


def test_parser_accepts_skip_only_keep_project_and_strict_remove_ui() -> None:
    parser = make_parser()
    args = parser.parse_args(
        [
            "--only",
            "source_add_text,ask",
            "--skip",
            "project_remove",
            "--keep-project",
            "--strict-remove-ui",
            "--step-delay-seconds",
            "0.25",
            "--service-base-url",
            "http://localhost:8000",
            "--service-token",
            "secret-token",
            "--service-timeout-seconds",
            "45",
        ]
    )
    assert args.only == ["source_add_text,ask"]
    assert args.skip == ["project_remove"]
    assert args.keep_project is True
    assert args.strict_remove_ui is True
    assert args.step_delay_seconds == 0.25
    assert args.service_base_url == "http://localhost:8000"
    assert args.service_token == "secret-token"
    assert args.service_timeout_seconds == 45.0


def test_resolve_step_selection_expands_aliases_and_forces_login_and_capabilities() -> None:
    selection = resolve_step_selection(
        only_values=["source_add_text,ask"],
        skip_values=[],
        keep_project=False,
    )
    assert selection.requested_only == ("source_add_text", "ask")
    assert selection.enabled_steps == (
        "login_check",
        "project_source_capabilities",
        "project_source_add_text",
        "ask_question",
    )


def test_resolve_step_selection_skips_cleanup_when_keep_project_enabled() -> None:
    selection = resolve_step_selection(
        only_values=[],
        skip_values=[],
        keep_project=True,
    )
    assert "project_remove_cleanup" not in selection.enabled_steps
    assert "login_check" in selection.enabled_steps


@pytest.mark.parametrize("token", ["does-not-exist", "source_add_text,unknown"])
def test_resolve_step_selection_rejects_unknown_steps(token: str) -> None:
    with pytest.raises(ValueError):
        resolve_step_selection(only_values=[token], skip_values=[], keep_project=False)


def test_resolve_step_selection_raises_when_all_steps_removed() -> None:
    with pytest.raises(ValueError):
        resolve_step_selection(only_values=["login"], skip_values=["login"], keep_project=False)
