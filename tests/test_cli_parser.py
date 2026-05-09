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


def test_parser_accepts_project_source_list_command() -> None:
    parser = make_parser()
    args = parser.parse_args(["project-source-list", "--json"])
    assert args.command == "project-source-list"
    assert args.json is True


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
        "./.pb_profile",
    ]
    normalized = _normalize_global_options(argv)
    assert normalized[:2] == ["--profile-dir", "./.pb_profile"]
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
    assert "0.0.194" in out
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
    assert args.profile == 'browser'


def test_parser_accepts_test_suite_full_profile() -> None:
    parser = make_parser()
    args = parser.parse_args(['test-suite', '--profile', 'full', '--path', '.', '--package-zip', 'release.zip'])
    assert args.command == 'test-suite'
    assert args.profile == 'full'
    assert args.path == '.'
    assert args.package_zip == 'release.zip'


def test_parser_accepts_canonical_test_profile_shortcuts() -> None:
    parser = make_parser()

    browser = parser.parse_args(['test', 'browser', '--json'])
    assert browser.command == 'test'
    assert browser.test_command == 'browser'
    assert browser.json is True

    agent = parser.parse_args(['test', 'agent', '--path', '.', '--package-zip', 'release.zip'])
    assert agent.command == 'test'
    assert agent.test_command == 'agent'
    assert agent.path == '.'
    assert agent.package_zip == 'release.zip'

    full = parser.parse_args(['test', 'full', '--json', '--keep-project'])
    assert full.command == 'test'
    assert full.test_command == 'full'
    assert full.json is True
    assert full.keep_project is True

    import_smoke = parser.parse_args(['test', 'import-smoke', '--path', '.', '--json'])
    assert import_smoke.command == 'test'
    assert import_smoke.test_command == 'import-smoke'
    assert import_smoke.path == '.'
    assert import_smoke.json is True


def test_parser_defaults_project_source_add_type_to_file() -> None:
    parser = make_parser()
    args = parser.parse_args(["project-source-add", "--file", "demo.zip"])
    assert args.command == "project-source-add"
    assert args.type == "file"
    assert args.file == "demo.zip"


def test_parser_accepts_project_source_add_positional_file() -> None:
    parser = make_parser()
    args = parser.parse_args(["project-source-add", "demo.zip"])
    assert args.command == "project-source-add"
    assert args.type == "file"
    assert args.file_path == "demo.zip"
    assert args.file is None


def test_phase2_parser_accepts_task_message_commands() -> None:
    parser = make_parser()

    messages_args = parser.parse_args(["task", "messages", "list", "--json"])
    assert messages_args.command == "task"
    assert messages_args.task_command == "messages"
    assert messages_args.task_messages_command == "list"
    assert messages_args.json is True

    message_show_args = parser.parse_args(["task", "message", "show", "2", "--json"])
    assert message_show_args.command == "task"
    assert message_show_args.task_command == "message"
    assert message_show_args.task_message_command == "show"
    assert message_show_args.id_or_index == "2"
    assert message_show_args.json is True

    answer_args = parser.parse_args(["task", "message", "answer", "abc", "--task", "Current chat"])
    assert answer_args.command == "task"
    assert answer_args.task_command == "message"
    assert answer_args.task_message_command == "answer"
    assert answer_args.id_or_index == "abc"
    assert answer_args.target == "Current chat"


def test_parser_accepts_phase3_src_sync_and_artifact_commands() -> None:
    parser = make_parser()
    src_sync = parser.parse_args(["src", "sync", ".", "--no-upload", "--force", "--json"])
    assert src_sync.command == "src"
    assert src_sync.src_command == "sync"
    assert src_sync.no_upload is True
    assert src_sync.force is True
    assert src_sync.json is True

    upload_sync = parser.parse_args(["src", "sync", ".", "--upload", "--confirm-upload", "--confirm-transaction-id", "abc123", "--json"])
    assert upload_sync.upload is True
    assert upload_sync.confirm_upload is True
    assert upload_sync.confirm_transaction_id == "abc123"

    artifact_adopt = parser.parse_args(["artifact", "adopt", "release.zip", "--from-project-source", "--local-path", "./release.zip", "--json"])
    assert artifact_adopt.command == "artifact"
    assert artifact_adopt.artifact_command == "adopt"
    assert artifact_adopt.artifact == "release.zip"
    assert artifact_adopt.from_project_source is True
    assert artifact_adopt.local_path == "./release.zip"
    assert artifact_adopt.json is True

    artifact_verify = parser.parse_args(["artifact", "verify", "release.zip", "--json"])
    assert artifact_verify.command == "artifact"
    assert artifact_verify.artifact_command == "verify"
    assert artifact_verify.path == "release.zip"
    assert artifact_verify.json is True


def test_parser_accepts_strict_task_visibility_escape_hatch() -> None:
    parser = make_parser()
    args = parser.parse_args(["test-suite", "--allow-recent-state-task-fallback"])
    assert args.command == "test-suite"
    assert args.allow_recent_state_task_fallback is True


def test_parser_accepts_agent_commands() -> None:
    parser = make_parser()
    inspect_args = parser.parse_args(["agent", "inspect", ".", "--json"])
    doctor_args = parser.parse_args(["agent", "doctor", ".", "--json"])
    plan_args = parser.parse_args(["agent", "plan", "sync repo", "--path", ".", "--json"])

    assert inspect_args.command == "agent"
    assert inspect_args.agent_command == "inspect"
    assert inspect_args.json is True
    assert doctor_args.agent_command == "doctor"
    assert plan_args.agent_command == "plan"
    assert plan_args.request == "sync repo"
    assert plan_args.path == "."


def test_parser_accepts_mcp_manifest_command() -> None:
    parser = make_parser()
    args = parser.parse_args(["mcp", "manifest", "--include-controlled-processes", "--json"])

    assert args.command == "mcp"
    assert args.mcp_command == "manifest"
    assert args.include_controlled_processes is True
    assert args.json is True


def test_parser_keeps_deprecated_controlled_writes_alias() -> None:
    parser = make_parser()
    args = parser.parse_args(["mcp", "manifest", "--include-controlled-writes", "--json"])

    assert args.command == "mcp"
    assert args.mcp_command == "manifest"
    assert args.include_controlled_processes is True
    assert args.json is True


def test_parser_accepts_mcp_config_command() -> None:
    parser = make_parser()
    args = parser.parse_args(["mcp", "config", "--path", ".", "--host", "claude-desktop", "--server-name", "pb", "--command", "promptbranch", "--json"])

    assert args.command == "mcp"
    assert args.mcp_command == "config"
    assert args.host == "claude-desktop"
    assert args.server_name == "pb"
    assert args.mcp_executable == "promptbranch"


def test_parser_accepts_ask_prompt_file_and_repeatable_attachments() -> None:
    parser = make_parser()
    args = parser.parse_args([
        "ask",
        "review",
        "--prompt-file",
        "prompt.md",
        "--attach",
        "one.log",
        "--attachment",
        "two.txt",
    ])
    assert args.command == "ask"
    assert args.prompt == "review"
    assert args.prompt_file == "prompt.md"
    assert args.attachments == ["one.log", "two.txt"]


def test_parser_accepts_agent_run_host_smoke_and_mcp_call() -> None:
    parser = make_parser()
    run_args = parser.parse_args(["agent", "run", "read VERSION", "--path", ".", "--skill", "repo-inspection", "--json"])
    host_args = parser.parse_args(["agent", "host-smoke", "--path", ".", "--json"])
    call_args = parser.parse_args(["agent", "mcp-call", "filesystem.read", '{"path":"VERSION"}', "--path", ".", "--json"])
    assert run_args.command == "agent"
    assert run_args.agent_command == "run"
    assert run_args.skill == "repo-inspection"
    assert host_args.agent_command == "host-smoke"
    assert call_args.agent_command == "mcp-call"
    assert call_args.tool == "filesystem.read"


def test_parser_accepts_skill_commands() -> None:
    parser = make_parser()
    list_args = parser.parse_args(["skill", "list", "--json"])
    show_args = parser.parse_args(["skill", "show", "repo-inspection", "--no-content", "--json"])
    validate_args = parser.parse_args(["skill", "validate", ".promptbranch/skills/repo-inspection", "--json"])
    assert list_args.command == "skill"
    assert list_args.skill_command == "list"
    assert show_args.skill == "repo-inspection"
    assert show_args.no_content is True
    assert validate_args.skill_command == "validate"


def test_parser_accepts_agent_summarize_log_command() -> None:
    parser = make_parser()
    args = parser.parse_args(["agent", "summarize-log", "session.log", "--path", ".", "--model", "fake", "--max-bytes", "4096", "--json"])
    assert args.command == "agent"
    assert args.agent_command == "summarize-log"
    assert args.log_path == "session.log"
    assert args.path == "."
    assert args.model == "fake"
    assert args.max_bytes == 4096
    assert args.json is True


def test_parser_accepts_rate_limit_safe_flags_for_test_full() -> None:
    parser = make_parser()
    enabled = parser.parse_args(["test", "full", "--rate-limit-safe"])
    assert enabled.rate_limit_safe is True
    disabled = parser.parse_args(["test", "full", "--no-rate-limit-safe"])
    assert disabled.rate_limit_safe is False


def test_parser_accepts_test_report_command() -> None:
    parser = make_parser()
    args = parser.parse_args(['test', 'report', 'pb_test.full.log', '--service-log', 'service.log', '--json'])
    assert args.command == 'test'
    assert args.test_command == 'report'
    assert args.log == 'pb_test.full.log'
    assert args.service_log == 'service.log'
    assert args.json is True


def test_parser_accepts_test_status_command() -> None:
    parser = make_parser()
    args = parser.parse_args(['test', 'status', '--path', '.', '--log', 'pb_test.full.log', '--service-log', 'service.log', '--json'])
    assert args.command == 'test'
    assert args.test_command == 'status'
    assert args.path == '.'
    assert args.log == 'pb_test.full.log'
    assert args.service_log == 'service.log'
    assert args.json is True


def test_parser_accepts_artifact_release_print_confirm_command() -> None:
    parser = make_parser()
    args = parser.parse_args([
        "artifact", "release", ".", "--sync-source", "--upload", "--print-confirm-command"
    ])

    assert args.command == "artifact"
    assert args.artifact_command == "release"
    assert args.sync_source is True
    assert args.upload is True
    assert args.print_confirm_command is True


def test_parser_accepts_artifact_release_confirm_command_only_alias() -> None:
    parser = make_parser()
    args = parser.parse_args([
        "artifact", "release", ".", "--sync-source", "--upload", "--confirm-command-only"
    ])

    assert args.command == "artifact"
    assert args.artifact_command == "release"
    assert args.print_confirm_command is True
