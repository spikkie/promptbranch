from __future__ import annotations

from promptbranch_cli import make_parser, _normalize_global_options
from promptbranch_version import PACKAGE_VERSION



def test_parser_accepts_queue_inspection_commands() -> None:
    parser = make_parser()

    status_args = parser.parse_args(["queue", "status", "--repo-path", ".", "--json"])
    list_args = parser.parse_args(["queue", "list", "--json"])
    plan_args = parser.parse_args([
        "queue",
        "plan",
        "--operation",
        "src_add",
        "--context",
        "account_id=default",
        "--context",
        "project_id=demo",
        "--context",
        "service_id=default",
        "--json",
    ])
    conflicts_args = parser.parse_args([
        "queue",
        "conflicts",
        "--left-operation",
        "src_add",
        "--right-operation",
        "src_sync",
        "--context",
        "project_id=demo",
        "--json",
    ])

    assert status_args.command == "queue"
    assert status_args.queue_command == "status"
    assert status_args.repo_path == "."
    assert list_args.queue_command == "list"
    assert plan_args.queue_command == "plan"
    assert plan_args.operation == "src_add"
    assert plan_args.context == ["account_id=default", "project_id=demo", "service_id=default"]
    assert conflicts_args.queue_command == "conflicts"
    assert conflicts_args.left_operation == "src_add"
    assert conflicts_args.right_operation == "src_sync"

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
    assert PACKAGE_VERSION in out
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

    artifact_roundtrip = parser.parse_args([
        '--profile-dir', '.pb_profile_test',
        'test', 'artifact-roundtrip', '--json', '--path', '.',
        '--run-id', 'UNIT',
    ])
    assert artifact_roundtrip.command == 'test'
    assert artifact_roundtrip.test_command == 'artifact-roundtrip'
    assert artifact_roundtrip.json is True
    assert artifact_roundtrip.path == '.'
    assert artifact_roundtrip.profile_dir == '.pb_profile_test'
    assert artifact_roundtrip.run_id == 'UNIT'


    ask_live = parser.parse_args(['test', 'ask-live', '--json', '--run-id', 'UNIT', '--only', 'plain,prompt_file'])
    assert ask_live.command == 'test'
    assert ask_live.test_command == 'ask-live'
    assert ask_live.json is True
    assert ask_live.run_id == 'UNIT'
    assert ask_live.only == ['plain,prompt_file']
    assert ask_live.project_name_prefix == 'itest-promptbranch-retained-delete-frozen'
    assert ask_live.memory_mode == 'project-only'
    assert ask_live.keep_project is False
    assert ask_live.debug_browser is True

    roundtrip = parser.parse_args([
        'test', 'visual-artifact-roundtrip', '--json', '--run-id', 'UNIT',
        '--output-filename', 'pb_visual_artifact_roundtrip_UNIT.zip',
        '--expect-entry', 'output.txt', '--expect-content', 'ZIP_OK',
    ])
    assert roundtrip.command == 'test'
    assert roundtrip.test_command == 'visual-artifact-roundtrip'
    assert roundtrip.json is True
    assert roundtrip.run_id == 'UNIT'
    assert roundtrip.output_filename == 'pb_visual_artifact_roundtrip_UNIT.zip'
    assert roundtrip.expect_entry == 'output.txt'
    assert roundtrip.expect_content == 'ZIP_OK'
    assert roundtrip.debug_browser is True
    assert roundtrip.keep_project is False  # parser flag remains false; command dispatch enforces keep-project while delete is frozen
    assert roundtrip.conversation_url is None
    assert roundtrip.project_name_prefix == 'itest-promptbranch-retained-delete-frozen'
    assert roundtrip.memory_mode == 'project-only'

    roundtrip_explicit = parser.parse_args([
        'test', 'visual-artifact-roundtrip', '--conversation-url',
        'https://chatgpt.com/g/g-p-11111111111111111111111111111111-x/c/y',
        '--keep-project',
    ])
    assert roundtrip_explicit.conversation_url.endswith('/c/y')
    assert roundtrip_explicit.keep_project is True


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

    parse_args = parser.parse_args(["task", "answer", "parse", "--latest", "--json"])
    assert parse_args.command == "task"
    assert parse_args.task_command == "answer"
    assert parse_args.task_answer_command == "parse"
    assert parse_args.latest is True
    assert parse_args.json is True


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

    artifact_intake = parser.parse_args([
        "artifact", "intake", "--from-last-answer", "--from-last-protocol-run", "--dry-run", "--expect-artifact", "release.zip", "--expect-version", "v0.0.209", "--expect-repo", "repo", "--message-id", "msg-1", "--answer-id", "ans-1", "--answer-index", "2", "--download", "--local-file", "/tmp/release.zip", "--download-timeout", "7", "--verify", "--migrate", "--repo-path", "/tmp/repo", "--json"
    ])
    assert artifact_intake.command == "artifact"
    assert artifact_intake.artifact_command == "intake"
    assert artifact_intake.from_last_answer is True
    assert artifact_intake.from_last_protocol_run is True
    assert artifact_intake.dry_run is True
    assert artifact_intake.expect_artifact == "release.zip"
    assert artifact_intake.expect_version == "v0.0.209"
    assert artifact_intake.expect_repo == "repo"
    assert artifact_intake.message_id == "msg-1"
    assert artifact_intake.answer_id == "ans-1"
    assert artifact_intake.answer_index == "2"
    assert artifact_intake.download is True
    assert artifact_intake.local_file == "/tmp/release.zip"
    assert artifact_intake.download_timeout == 7.0
    assert artifact_intake.verify is True
    assert artifact_intake.migrate is True
    assert artifact_intake.repo_path == "/tmp/repo"
    assert artifact_intake.json is True

    artifact_candidate_test = parser.parse_args([
        "artifact", "candidate-test", "chatgpt_claudecode_workflow_v0.0.209.zip",
        "--version", "v0.0.209",
        "--repo-path", "/tmp/repo",
        "--preflight-only",
        "--profile", "full",
        "--test-timeout", "123",
        "--release-log-keep", "7",
        "--json",
    ])
    assert artifact_candidate_test.command == "artifact"
    assert artifact_candidate_test.artifact_command == "candidate-test"
    assert artifact_candidate_test.artifact == "chatgpt_claudecode_workflow_v0.0.209.zip"
    assert artifact_candidate_test.version == "v0.0.209"
    assert artifact_candidate_test.repo_path == "/tmp/repo"
    assert artifact_candidate_test.preflight_only is True
    assert artifact_candidate_test.profile == "full"
    assert artifact_candidate_test.test_timeout == 123.0
    assert artifact_candidate_test.release_log_keep == 7
    assert artifact_candidate_test.json is True


    artifact_candidate_status = parser.parse_args([
        "artifact", "candidate-status", "chatgpt_claudecode_workflow_v0.0.230.zip",
        "--version", "v0.0.230",
        "--repo-path", "/tmp/repo",
        "--json",
    ])
    assert artifact_candidate_status.command == "artifact"
    assert artifact_candidate_status.artifact_command == "candidate-status"
    assert artifact_candidate_status.artifact == "chatgpt_claudecode_workflow_v0.0.230.zip"
    assert artifact_candidate_status.version == "v0.0.230"
    assert artifact_candidate_status.all is False
    assert artifact_candidate_status.repo_path == "/tmp/repo"
    assert artifact_candidate_status.json is True

    artifact_candidate_status_all = parser.parse_args([
        "artifact", "candidate-status",
        "--all",
        "--repo-path", "/tmp/repo",
        "--json",
    ])
    assert artifact_candidate_status_all.command == "artifact"
    assert artifact_candidate_status_all.artifact_command == "candidate-status"
    assert artifact_candidate_status_all.artifact is None
    assert artifact_candidate_status_all.all is True
    assert artifact_candidate_status_all.repo_path == "/tmp/repo"
    assert artifact_candidate_status_all.json is True


    artifact_mvp_status = parser.parse_args([
        "artifact", "mvp-status",
        "chatgpt_claudecode_workflow_v0.0.247.zip",
        "--version", "v0.0.247",
        "--repo-path", "/tmp/repo",
        "--json",
    ])
    assert artifact_mvp_status.command == "artifact"
    assert artifact_mvp_status.artifact_command == "mvp-status"
    assert artifact_mvp_status.artifact == "chatgpt_claudecode_workflow_v0.0.247.zip"
    assert artifact_mvp_status.version == "v0.0.247"
    assert artifact_mvp_status.repo_path == "/tmp/repo"
    assert artifact_mvp_status.json is True

    artifact_mvp_dod = parser.parse_args([
        "artifact", "mvp-dod",
        "--repo-path", "/tmp/repo",
        "--json",
    ])
    assert artifact_mvp_dod.command == "artifact"
    assert artifact_mvp_dod.artifact_command == "mvp-dod"
    assert artifact_mvp_dod.repo_path == "/tmp/repo"
    assert artifact_mvp_dod.json is True



def test_parser_accepts_release_baseline_status_command() -> None:
    parser = make_parser()
    args = parser.parse_args([
        "release", "baseline-status",
        "--version", "v0.1.10",
        "--artifact", "chatgpt_claudecode_workflow-2_v0.1.10.zip",
        "--include-docs",
        "--repo-path", "/tmp/repo",
        "--json",
    ])
    assert args.command == "release"
    assert args.release_command == "baseline-status"
    assert args.version == "v0.1.10"
    assert args.artifact == "chatgpt_claudecode_workflow-2_v0.1.10.zip"
    assert args.include_docs is True
    assert args.repo_path == "/tmp/repo"
    assert args.json is True


def test_parser_accepts_release_docs_status_command() -> None:
    parser = make_parser()
    args = parser.parse_args([
        "release", "docs-status",
        "--version", "v0.1.8",
        "--design-doc", "docs/design/promptbranch-mvp-living-design.md",
        "--drawio", "docs/design/promptbranch-mvp-living-design.drawio",
        "--repo-path", "/tmp/repo",
        "--json",
    ])
    assert args.command == "release"
    assert args.release_command == "docs-status"
    assert args.version == "v0.1.8"
    assert args.design_doc == "docs/design/promptbranch-mvp-living-design.md"
    assert args.drawio == "docs/design/promptbranch-mvp-living-design.drawio"
    assert args.repo_path == "/tmp/repo"
    assert args.json is True


def test_parser_accepts_release_dev_status_command() -> None:
    parser = make_parser()
    args = parser.parse_args([
        "release", "dev-status",
        "--artifact", "chatgpt_claudecode_workflow-2_v0.1.5.zip",
        "--config", ".promptbranch-release.yml",
        "--repo-path", "/tmp/repo",
        "--json",
    ])
    assert args.command == "release"
    assert args.release_command == "dev-status"
    assert args.artifact == "chatgpt_claudecode_workflow-2_v0.1.5.zip"
    assert args.config == ".promptbranch-release.yml"
    assert args.repo_path == "/tmp/repo"
    assert args.json is True


def test_parser_accepts_release_status_guide_command() -> None:
    parser = make_parser()
    args = parser.parse_args([
        "release", "status-guide",
        "--artifact", "chatgpt_claudecode_workflow-2_v0.1.14.zip",
        "--version", "v0.1.14",
        "--target-version", "v0.1.14",
        "--config", ".promptbranch-release.yml",
        "--repo-path", "/tmp/repo",
        "--json",
    ])
    assert args.command == "release"
    assert args.release_command == "status-guide"
    assert args.artifact == "chatgpt_claudecode_workflow-2_v0.1.14.zip"
    assert args.version == "v0.1.14"
    assert args.target_version == "v0.1.14"
    assert args.config == ".promptbranch-release.yml"
    assert args.repo_path == "/tmp/repo"
    assert args.json is True


def test_parser_accepts_release_checkpoint_command() -> None:
    parser = make_parser()
    args = parser.parse_args([
        "release", "checkpoint",
        "--artifact", "chatgpt_claudecode_workflow-2_v0.1.6.zip",
        "--version", "v0.1.6",
        "--target-version", "v0.1.6",
        "--mode", "continue",
        "--config", ".promptbranch-release.yml",
        "--repo-path", "/tmp/repo",
        "--json",
    ])
    assert args.command == "release"
    assert args.release_command == "checkpoint"
    assert args.artifact == "chatgpt_claudecode_workflow-2_v0.1.6.zip"
    assert args.version == "v0.1.6"
    assert args.target_version == "v0.1.6"
    assert args.mode == "continue"
    assert args.config == ".promptbranch-release.yml"
    assert args.repo_path == "/tmp/repo"
    assert args.json is True


def test_parser_accepts_release_lifecycle_status_command() -> None:
    parser = make_parser()
    args = parser.parse_args([
        "release", "lifecycle-status",
        "--version", "v0.0.274",
        "--target-version", "v0.0.274",
        "--repo-path", "/tmp/repo",
        "--include-service-health",
        "--include-project-sources",
        "--json",
    ])
    assert args.command == "release"
    reconcile_args = parser.parse_args([
        "release", "reconcile-current",
        "--artifact", "./chatgpt_claudecode_workflow-2_v0.1.50.zip",
        "--version", "v0.1.50",
        "--target-version", "v0.1.51",
        "--repo-path", "/tmp/repo",
        "--profile-dir", "/tmp/profile",
        "--json",
    ])
    assert reconcile_args.command == "release"
    assert reconcile_args.release_command == "reconcile-current"
    assert reconcile_args.artifact == "./chatgpt_claudecode_workflow-2_v0.1.50.zip"
    assert reconcile_args.version == "v0.1.50"
    assert reconcile_args.target_version == "v0.1.51"
    assert reconcile_args.repo_path == "/tmp/repo"
    assert reconcile_args.profile_dir == "/tmp/profile"
    assert reconcile_args.json is True

    assert args.release_command == "lifecycle-status"
    assert args.version == "v0.0.274"
    assert args.target_version == "v0.0.274"
    assert args.repo_path == "/tmp/repo"
    assert args.include_service_health is True
    assert args.include_project_sources is True
    assert args.json is True

    artifact_candidate_next = parser.parse_args([
        "artifact", "candidate-next",
        "chatgpt_claudecode_workflow_v0.0.230.zip",
        "--version", "v0.0.230",
        "--repo-path", "/tmp/repo",
        "--json",
    ])
    assert artifact_candidate_next.command == "artifact"
    assert artifact_candidate_next.artifact_command == "candidate-next"
    assert artifact_candidate_next.artifact == "chatgpt_claudecode_workflow_v0.0.230.zip"
    assert artifact_candidate_next.version == "v0.0.230"
    assert artifact_candidate_next.repo_path == "/tmp/repo"
    assert artifact_candidate_next.json is True

    artifact_candidate_run = parser.parse_args([
        "artifact", "candidate-run",
        "chatgpt_claudecode_workflow_v0.0.230.zip",
        "--version", "v0.0.230",
        "--repo-path", "/tmp/repo",
        "--execute-next",
        "--execute-until-blocked",
        "--max-steps", "3",
        "--require-complete",
        "--require-real-candidate",
        "--profile", "full",
        "--accept-if-green",
        "--step-timeout", "123",
        "--json",
    ])
    assert artifact_candidate_run.command == "artifact"
    assert artifact_candidate_run.artifact_command == "candidate-run"
    assert artifact_candidate_run.artifact == "chatgpt_claudecode_workflow_v0.0.230.zip"
    assert artifact_candidate_run.version == "v0.0.230"
    assert artifact_candidate_run.repo_path == "/tmp/repo"
    assert artifact_candidate_run.execute_next is True
    assert artifact_candidate_run.execute_until_blocked is True
    assert artifact_candidate_run.max_steps == 3
    assert artifact_candidate_run.require_complete is True
    assert artifact_candidate_run.require_real_candidate is True
    assert artifact_candidate_run.profile == "full"
    assert artifact_candidate_run.accept_if_green is True
    assert artifact_candidate_run.step_timeout == 123.0
    assert artifact_candidate_run.json is True

    artifact_accept_candidate = parser.parse_args([
        "artifact", "accept-candidate", "chatgpt_claudecode_workflow_v0.0.209.zip",
        "--version", "v0.0.209",
        "--repo-path", "/tmp/repo",
        "--from-project-source",
        "--run-release-control",
        "--adopt-if-green",
        "--profile", "full",
        "--test-timeout", "123",
        "--release-log-keep", "7",
        "--json",
    ])
    assert artifact_accept_candidate.command == "artifact"
    assert artifact_accept_candidate.artifact_command == "accept-candidate"
    assert artifact_accept_candidate.artifact == "chatgpt_claudecode_workflow_v0.0.209.zip"
    assert artifact_accept_candidate.version == "v0.0.209"
    assert artifact_accept_candidate.repo_path == "/tmp/repo"
    assert artifact_accept_candidate.from_project_source is True
    assert artifact_accept_candidate.run_release_control is True
    assert artifact_accept_candidate.adopt_if_green is True
    assert artifact_accept_candidate.test_timeout == 123.0
    assert artifact_accept_candidate.release_log_keep == 7
    assert artifact_accept_candidate.json is True


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


def test_parser_accepts_protocol_ask_generation_flags() -> None:
    parser = make_parser()
    args = parser.parse_args([
        "ask",
        "continue next slice",
        "--protocol",
        "--from-current-baseline",
        "--target-version",
        "v0.0.209",
        "--print-request-json",
        "--parse-reply",
        "--answer-index",
        "latest",
    ])
    assert args.command == "ask"
    assert args.protocol is True
    assert args.from_current_baseline is True
    assert args.target_version == "v0.0.209"
    assert args.print_request_json is True
    assert args.parse_reply is True
    assert args.answer_index == "latest"


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




def test_parser_accepts_agent_release_readiness_command() -> None:
    parser = make_parser()
    args = parser.parse_args(["agent", "release-readiness", "--path", ".", "--require-ready", "--json"])
    assert args.command == "agent"
    assert args.agent_command == "release-readiness"
    assert args.path == "."
    assert args.require_ready is True
    assert args.json is True

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


def test_parser_accepts_release_doctor_command() -> None:
    parser = make_parser()
    args = parser.parse_args([
        "release", "doctor",
        "--version", "v0.0.247",
        "--target-version", "v0.0.257",
        "--artifact", "chatgpt_claudecode_workflow_v0.0.247.zip",
        "--repo-path", "/tmp/repo",
        "--skip-service-health",
        "--skip-project-sources",
        "--json",
    ])

    assert args.command == "release"
    assert args.release_command == "doctor"
    assert args.version == "v0.0.247"
    assert args.target_version == "v0.0.257"
    assert args.artifact == "chatgpt_claudecode_workflow_v0.0.247.zip"
    assert args.repo_path == "/tmp/repo"
    assert args.skip_service_health is True
    assert args.skip_project_sources is True
    assert args.json is True




def test_parser_accepts_release_install_plan_command() -> None:
    parser = make_parser()
    args = parser.parse_args([
        "release", "install",
        "--artifact", "chatgpt_claudecode_workflow_v0.0.257.zip",
        "--version", "v0.0.257",
        "--target-version", "v0.0.257",
        "--config", ".promptbranch-release.yml",
        "--repo-path", "/tmp/repo",
        "--plan",
        "--upload-source",
        "--keep-open",
        "--json",
    ])

    assert args.command == "release"
    assert args.release_command == "install"
    assert args.artifact == "chatgpt_claudecode_workflow_v0.0.257.zip"
    assert args.version == "v0.0.257"
    assert args.target_version == "v0.0.257"
    assert args.config == ".promptbranch-release.yml"
    assert args.repo_path == "/tmp/repo"
    assert args.plan is True
    assert args.upload_source is True
    assert args.keep_open is True
    assert args.json is True


def test_parser_accepts_release_test_command() -> None:
    parser = make_parser()
    args = parser.parse_args([
        "release", "test",
        "--artifact", "chatgpt_claudecode_workflow_v0.0.257.zip",
        "--version", "v0.0.257",
        "--target-version", "v0.0.257",
        "--config", ".promptbranch-release.yml",
        "--repo-path", "/tmp/repo",
        "--hook", "preflight",
        "--hook", "local_acceptance",
        "--hook-timeout", "42",
        "--no-stop-on-failure",
        "--json",
    ])

    assert args.command == "release"
    assert args.release_command == "test"
    assert args.artifact == "chatgpt_claudecode_workflow_v0.0.257.zip"
    assert args.version == "v0.0.257"
    assert args.target_version == "v0.0.257"
    assert args.config == ".promptbranch-release.yml"
    assert args.repo_path == "/tmp/repo"
    assert args.hook == ["preflight", "local_acceptance"]
    assert args.hook_timeout == 42
    assert args.stop_on_failure is False
    assert args.json is True


def test_parser_accepts_release_adopt_command() -> None:
    parser = make_parser()
    args = parser.parse_args([
        "release", "adopt",
        "--artifact", "chatgpt_claudecode_workflow_v0.0.257.zip",
        "--version", "v0.0.257",
        "--target-version", "v0.0.257",
        "--acceptance-report", ".pb_profile/release_acceptance/v0.0.257/release_acceptance.fixture.json",
        "--repo-path", "/tmp/repo",
        "--plan",
        "--keep-open",
        "--json",
    ])

    assert args.command == "release"
    assert args.release_command == "adopt"
    assert args.artifact == "chatgpt_claudecode_workflow_v0.0.257.zip"
    assert args.version == "v0.0.257"
    assert args.target_version == "v0.0.257"
    assert args.acceptance_report.endswith("release_acceptance.fixture.json")
    assert args.repo_path == "/tmp/repo"
    assert args.plan is True
    assert args.keep_open is True
    assert args.json is True


def test_parser_accepts_release_config_command() -> None:
    parser = make_parser()
    args = parser.parse_args([
        "release", "config",
        "--config", ".promptbranch-release.yml",
        "--repo-path", "/tmp/repo",
        "--json",
    ])

    assert args.command == "release"
    assert args.release_command == "config"
    assert args.config == ".promptbranch-release.yml"
    assert args.repo_path == "/tmp/repo"
    assert args.json is True


def test_parser_accepts_ask_release_strict_candidate_request() -> None:
    parser = make_parser()
    args = parser.parse_args([
        "ask-release",
        "Implement the next candidate-producing slice.",
        "--target-version", "v0.0.257",
        "--baseline-artifact", "chatgpt_claudecode_workflow_v0.0.256.zip",
        "--baseline-version", "v0.0.256",
        "--expect-artifact", "chatgpt_claudecode_workflow_v0.0.257.zip",
        "--expect-repo", "chatgpt_claudecode_workflow",
        "--expect-version", "v0.0.257",
        "--print-request-json",
        "--json",
    ])

    assert args.command == "ask-release"
    assert args.target_version == "v0.0.257"
    assert args.baseline_artifact == "chatgpt_claudecode_workflow_v0.0.256.zip"
    assert args.baseline_version == "v0.0.256"
    assert args.expect_artifact == "chatgpt_claudecode_workflow_v0.0.257.zip"
    assert args.expect_repo == "chatgpt_claudecode_workflow"
    assert args.expect_version == "v0.0.257"
    assert args.print_request_json is True
    assert args.json is True


def test_task_answer_parse_parser_accepts_answer_selectors() -> None:
    args = make_parser().parse_args(["task", "answer", "parse", "42", "--answer-index", "2", "--answer-id", "abc", "--json"])
    assert args.command == "task"
    assert args.task_command == "answer"
    assert args.task_answer_command == "parse"
    assert args.id_or_index == "42"
    assert args.answer_index == "2"
    assert args.answer_id == "abc"
    assert args.json is True


def test_task_answer_parse_parser_accepts_explicit_message_selectors() -> None:
    args = make_parser().parse_args(["task", "answer", "parse", "--message-id", "msg-1", "--answer-id", "ans-1", "--json"])
    assert args.command == "task"
    assert args.task_command == "answer"
    assert args.task_answer_command == "parse"
    assert args.id_or_index is None
    assert args.message_id == "msg-1"
    assert args.answer_id == "ans-1"
    assert args.json is True

    args = make_parser().parse_args(["task", "answer", "parse", "--message-index", "7", "--answer-index", "2", "--json"])
    assert args.message_index == "7"
    assert args.answer_index == "2"


def test_parser_accepts_browser_status_and_source_add_profile_wait() -> None:
    parser = make_parser()

    status = parser.parse_args(["browser", "status", "--json"])
    assert status.command == "browser"
    assert status.browser_command == "status"
    assert status.json is True

    wait_idle = parser.parse_args(["browser", "wait-idle", "--timeout", "5", "--poll-seconds", "0.25", "--json"])
    assert wait_idle.command == "browser"
    assert wait_idle.browser_command == "wait-idle"
    assert wait_idle.timeout == 5
    assert wait_idle.poll_seconds == 0.25
    assert wait_idle.json is True

    src_add = parser.parse_args([
        "src",
        "add",
        "--file",
        "demo.zip",
        "--wait-for-profile",
        "--profile-wait-timeout-seconds",
        "120",
    ])
    assert src_add.command == "src"
    assert src_add.src_command == "add"
    assert src_add.wait_for_profile is True
    assert src_add.profile_wait_timeout_seconds == 120
    assert src_add.no_post_mutation_wait_idle is False
    assert src_add.post_mutation_idle_timeout_seconds == 180.0

    no_queue = parser.parse_args(["src", "add", "--file", "demo.zip", "--no-queue"])
    assert no_queue.no_queue is True


def test_global_options_after_browser_status_are_normalized() -> None:
    normalized = _normalize_global_options(["browser", "status", "--service-timeout-seconds", "1200", "--json"])
    assert normalized[:2] == ["--service-timeout-seconds", "1200"]
    assert normalized[2:4] == ["browser", "status"]


def test_parser_accepts_ask_debug_browser_flags() -> None:
    parser = make_parser()
    args = parser.parse_args([
        "ask",
        "hello",
        "--debug-browser",
        "--pause-after-fill",
        "--pause-before-submit",
    ])
    assert args.command == "ask"
    assert args.debug_browser is True
    assert args.pause_after_fill is True
    assert args.pause_before_submit is True



def test_parser_accepts_profile_pool_for_parallel_task_commands() -> None:
    parser = make_parser()

    task_list = parser.parse_args([
        "task", "list", "--json", "--profile-pool", "tasks", "--profile-pool-size", "3"
    ])
    assert task_list.command == "task"
    assert task_list.task_command == "list"
    assert task_list.profile_pool == "tasks"
    assert task_list.profile_pool_size == 3

    task_show = parser.parse_args([
        "task", "show", "1", "--profile-pool", "tasks", "--profile-pool-refresh"
    ])
    assert task_show.task_command == "show"
    assert task_show.profile_pool == "tasks"
    assert task_show.profile_pool_refresh is True


def test_parser_accepts_release_live_profile_pool_defaults() -> None:
    parser = make_parser()
    args = parser.parse_args(["test", "release-live", "--json", "--run-id", "UNIT"])
    assert args.command == "test"
    assert args.test_command == "release-live"
    assert args.profile_pool == "release-live"
    assert args.profile_pool_size == 2
    assert args.project_name_prefix == "itest-promptbranch-retained-delete-frozen"
    assert args.debug_browser is True



def test_parser_accepts_ask_live_profile_pool_when_requested() -> None:
    parser = make_parser()
    args = parser.parse_args(["test", "ask-live", "--json", "--run-id", "UNIT", "--profile-pool", "release-live"])
    assert args.command == "test"
    assert args.test_command == "ask-live"
    assert args.profile_pool == "release-live"
    assert args.profile_pool_size == 2
    assert args.project_name_prefix == "itest-promptbranch-retained-delete-frozen"
    assert args.debug_browser is True

def test_parser_accepts_debug_rate_limit_command() -> None:
    parser = make_parser()
    args = parser.parse_args(["debug", "rate-limit", "--json", "--probe-backend", "--wait-ms", "25", "--keep-open"])
    assert args.command == "debug"
    assert args.debug_command == "rate-limit"
    assert args.json is True
    assert args.probe_backend is True
    assert args.wait_ms == 25
    assert args.keep_open is True


def test_parser_accepts_debug_parallel_plan_command() -> None:
    parser = make_parser()
    args = parser.parse_args(["debug", "parallel-plan", "--operation", "src_add", "--json"])

    assert args.command == "debug"
    assert args.debug_command == "parallel-plan"
    assert args.operation == "src_add"
    assert args.json is True


def test_parser_accepts_profile_registry_commands() -> None:
    parser = make_parser()

    list_args = parser.parse_args(["profile", "list", "--repo-path", ".", "--json"])
    pools_args = parser.parse_args(["profile", "pools", "--profile", "local-debug", "--json"])
    show_args = parser.parse_args(["profile", "show", "service-default", "--json"])

    assert list_args.command == "profile"
    assert list_args.profile_command == "list"
    assert list_args.repo_path == "."
    assert list_args.json is True
    assert pools_args.profile_command == "pools"
    assert pools_args.profile == "local-debug"
    assert show_args.profile_command == "show"
    assert show_args.name == "service-default"

def test_parser_accepts_src_add_json_for_queue_smoke_contract() -> None:
    parser = make_parser()
    args = parser.parse_args([
        "src",
        "add",
        "--file",
        "demo.zip",
        "--profile-wait-timeout-seconds",
        "600",
        "--json",
    ])
    assert args.command == "src"
    assert args.src_command == "add"
    assert args.file == "demo.zip"
    assert args.profile_wait_timeout_seconds == 600
    assert args.json is True


def test_parser_accepts_project_source_add_json_for_legacy_contract() -> None:
    parser = make_parser()
    args = parser.parse_args([
        "project-source-add",
        "--file",
        "demo.zip",
        "--profile-wait-timeout-seconds",
        "600",
        "--json",
    ])
    assert args.command == "project-source-add"
    assert args.file == "demo.zip"
    assert args.profile_wait_timeout_seconds == 600
    assert args.json is True


def test_parser_accepts_debug_backend_reads_command() -> None:
    parser = make_parser()
    args = parser.parse_args(["debug", "backend-reads", "--operation", "task_list", "--plan-only", "--json"])

    assert args.command == "debug"
    assert args.debug_command == "backend-reads"
    assert args.operation == "task_list"
    assert args.plan_only is True
    assert args.json is True


def test_parser_accepts_parallel_task_show_command() -> None:
    parser = make_parser()
    args = parser.parse_args([
        "parallel",
        "task",
        "show",
        "1,2",
        "--task",
        "abc",
        "--targets",
        "def,ghi",
        "--concurrency",
        "3",
        "--plan-only",
        "--json",
    ])

    assert args.command == "parallel"
    assert args.parallel_command == "task"
    assert args.parallel_task_command == "show"
    assert args.target_values == ["1,2"]
    assert args.task == ["abc"]
    assert args.targets == ["def,ghi"]
    assert args.concurrency == 3
    assert args.plan_only is True
    assert args.json is True


def test_parser_accepts_parallel_ask_plan_command() -> None:
    parser = make_parser()
    args = parser.parse_args([
        "parallel",
        "ask",
        "summarize",
        "status",
        "--task",
        "1",
        "--targets",
        "2,3",
        "--concurrency",
        "2",
        "--plan-only",
        "--protocol",
        "--target-version",
        "v0.1.48",
        "--json",
    ])

    assert args.command == "parallel"
    assert args.parallel_command == "ask"
    assert args.prompt == ["summarize", "status"]
    assert args.task == ["1"]
    assert args.targets == ["2,3"]
    assert args.concurrency == 2
    assert args.plan_only is True
    assert args.protocol is True
    assert args.target_version == "v0.1.48"
    assert args.intent_kind == "parallel_task_request"
    assert args.json is True


def test_parser_accepts_src_queue_plan_command() -> None:
    parser = make_parser()
    args = parser.parse_args([
        "src",
        "queue-plan",
        "--operation",
        "add",
        "--workspace-url",
        "https://chatgpt.com/g/g-p-demo/project",
        "--file",
        "demo.zip",
        "--name",
        "demo.zip",
        "--json",
    ])

    assert args.command == "src"
    assert args.src_command == "queue-plan"
    assert args.operation == "add"
    assert args.workspace_url.endswith("/project")
    assert args.file == "demo.zip"
    assert args.json is True


def test_parser_accepts_release_lifecycle_dry_run_scheduler_context() -> None:
    parser = make_parser()
    args = parser.parse_args([
        "release",
        "lifecycle",
        "--artifact",
        "demo.zip",
        "--version",
        "v0.1.50",
        "--workspace-url",
        "https://chatgpt.com/g/g-p-demo/project",
        "--service-id",
        "default",
        "--dry-run",
        "--json",
    ])

    assert args.command == "release"
    assert args.release_command == "lifecycle"
    assert args.artifact == "demo.zip"
    assert args.version == "v0.1.50"
    assert args.workspace_url.endswith("/project")
    assert args.service_id == "default"
    assert args.plan is True
    assert args.json is True


def test_parser_accepts_orchestration_accept_event_dry_run_command() -> None:
    parser = make_parser()
    args = parser.parse_args(["orchestration", "accept-event", "--dry-run", "--json"])
    assert args.command == "orchestration"
    assert args.orchestration_command == "accept-event"
    assert args.dry_run is True
    assert args.json is True
    assert args.paths == []
