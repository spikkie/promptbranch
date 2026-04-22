from __future__ import annotations

from promptbranch_cli import make_parser, _normalize_global_options


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


def test_global_options_after_project_remove_are_normalized() -> None:
    argv = [
        "project-remove",
        "--dotenv",
        ".env",
    ]
    normalized = _normalize_global_options(argv)
    assert normalized[:2] == ["--dotenv", ".env"]
    assert "project-remove" in normalized


def test_parser_accepts_project_remove_command() -> None:
    parser = make_parser()
    args = parser.parse_args(["project-remove"])
    assert args.command == "project-remove"


def test_global_options_after_ask_include_config() -> None:
    argv = [
        "ask",
        "hello",
        "--config",
        "config.json",
    ]
    normalized = _normalize_global_options(argv)
    assert normalized[:2] == ["--config", "config.json"]
    assert normalized[2:] == ["ask", "hello"]


def test_parser_accepts_config_option() -> None:
    parser = make_parser()
    args = parser.parse_args(["--config", "config.json", "ask", "hello"])
    assert args.config == "config.json"
    assert args.command == "ask"


def test_parser_accepts_ask_conversation_url_option() -> None:
    parser = make_parser()
    args = parser.parse_args(["ask", "hello", "--conversation-url", "https://chatgpt.com/g/demo/c/123"])
    assert args.command == "ask"
    assert args.conversation_url == "https://chatgpt.com/g/demo/c/123"


def test_parser_accepts_use_and_completion_commands() -> None:
    parser = make_parser()
    use_args = parser.parse_args(["use", "My Project", "--conversation-url", "https://chatgpt.com/g/demo/c/123", "--json"])
    completion_args = parser.parse_args(["completion", "bash"])
    assert use_args.command == "use"
    assert use_args.target == "My Project"
    assert use_args.conversation_url == "https://chatgpt.com/g/demo/c/123"
    assert use_args.json is True
    assert completion_args.command == "completion"
    assert completion_args.shell == "bash"


def test_global_options_after_use_are_normalized() -> None:
    argv = [
        "use",
        "My Project",
        "--profile-dir",
        "./profile",
    ]
    normalized = _normalize_global_options(argv)
    assert normalized[:2] == ["--profile-dir", "./profile"]
    assert normalized[2:] == ["use", "My Project"]


def test_parser_accepts_project_list_command() -> None:
    parser = make_parser()
    args = parser.parse_args(["project-list", "--json"])
    assert args.command == "project-list"
    assert args.json is True


def test_global_options_after_project_list_are_normalized() -> None:
    argv = [
        "project-list",
        "--service-base-url",
        "http://localhost:8000",
    ]
    normalized = _normalize_global_options(argv)
    assert normalized[:2] == ["--service-base-url", "http://localhost:8000"]
    assert normalized[2:] == ["project-list"]


def test_parser_accepts_project_list_current_and_use_pick() -> None:
    parser = make_parser()
    project_list_args = parser.parse_args(["project-list", "--current"])
    use_args = parser.parse_args(["use", "--pick", "alpha", "--json"])
    assert project_list_args.command == "project-list"
    assert project_list_args.current is True
    assert use_args.command == "use"
    assert use_args.pick is True
    assert use_args.target == "alpha"
    assert use_args.json is True


def test_global_options_after_project_list_current_are_normalized() -> None:
    argv = [
        "project-list",
        "--current",
        "--service-base-url",
        "http://localhost:8000",
    ]
    normalized = _normalize_global_options(argv)
    assert normalized[:2] == ["--service-base-url", "http://localhost:8000"]
    assert normalized[2:] == ["project-list", "--current"]


def test_parser_version_option_outputs_release(capsys) -> None:
    parser = make_parser()
    try:
        parser.parse_args(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
    out = capsys.readouterr().out
    assert "0.0.96" in out
    assert "promptbranch" in out


def test_parser_accepts_version_subcommand() -> None:
    parser = make_parser()
    args = parser.parse_args(["version"])
    assert args.command == "version"


def test_main_help_command_prints_top_level_help(capsys) -> None:
    exit_code = __import__("promptbranch_cli").main(["help"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "usage: promptbranch" in captured.out
    assert "project-source-add" in captured.out


def test_main_help_command_prints_subcommand_help(capsys) -> None:
    exit_code = __import__("promptbranch_cli").main(["help", "project-source-add"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "usage: promptbranch project-source-add" in captured.out
    assert "--file" in captured.out


def test_parser_accepts_chat_command_family_and_aliases() -> None:
    parser = make_parser()
    assert parser.parse_args(["chat-list"]).command == "chat-list"
    assert parser.parse_args(["chats"]).command == "chats"
    chat_use = parser.parse_args(["chat-use", "123abc", "--json"])
    assert chat_use.command == "chat-use"
    assert chat_use.target == "123abc"
    assert chat_use.json is True
    assert parser.parse_args(["use-chat", "123abc"]).command == "use-chat"
    assert parser.parse_args(["chat-leave"]).command == "chat-leave"
    assert parser.parse_args(["cq"]).command == "cq"
    assert parser.parse_args(["chat-show"]).command == "chat-show"
    assert parser.parse_args(["show"]).command == "show"
    assert parser.parse_args(["chat-summarize"]).command == "chat-summarize"
    assert parser.parse_args(["summarize"]).command == "summarize"


def test_parser_accepts_test_suite_command() -> None:
    parser = make_parser()
    args = parser.parse_args(['test-suite', '--keep-project', '--only', 'project_list_debug'])
    assert args.command == 'test-suite'
    assert args.keep_project is True
    assert args.only == ['project_list_debug']


def test_parser_defaults_project_source_add_type_to_file() -> None:
    parser = make_parser()
    args = parser.parse_args(["project-source-add", "--file", "demo.zip"])
    assert args.command == "project-source-add"
    assert args.type == "file"
    assert args.file == "demo.zip"
