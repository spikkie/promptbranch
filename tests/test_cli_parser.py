from __future__ import annotations

from chatgpt_cli import make_parser, _normalize_global_options


def test_global_options_after_project_source_add_are_normalized() -> None:
    argv = [
        "project-source-add",
        "--type",
        "link",
        "--value",
        "https://example.com",
        "--dotenv",
        ".env",
    ]
    normalized = _normalize_global_options(argv)
    assert normalized[:2] == ["--dotenv", ".env"]
    assert "project-source-add" in normalized


def test_parser_accepts_project_source_remove_command() -> None:
    parser = make_parser()
    args = parser.parse_args(["project-source-remove", "Notes", "--exact"])
    assert args.command == "project-source-remove"
    assert args.source_name == "Notes"
    assert args.exact is True


def test_global_options_after_project_create_are_normalized() -> None:
    argv = [
        "project-create",
        "My Project",
        "--memory-mode",
        "project-only",
        "--dotenv",
        ".env",
    ]
    normalized = _normalize_global_options(argv)
    assert normalized[:2] == ["--dotenv", ".env"]
    assert "project-create" in normalized


def test_parser_accepts_project_create_command() -> None:
    parser = make_parser()
    args = parser.parse_args(["project-create", "My Project", "--memory-mode", "project-only"])
    assert args.command == "project-create"
    assert args.name == "My Project"
    assert args.memory_mode == "project-only"
