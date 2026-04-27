from __future__ import annotations

import argparse
import json
import pytest
from pathlib import Path


@pytest.fixture(autouse=True)
def _isolate_cli_defaults(monkeypatch, tmp_path) -> None:
    """Keep tests hermetic when a developer has Promptbranch defaults configured locally."""
    monkeypatch.setenv("CHATGPT_CLI_CONFIG", str(tmp_path / "missing-cli-config.json"))
    monkeypatch.delenv("CHATGPT_SERVICE_TIMEOUT_SECONDS", raising=False)

from promptbranch_cli import build_backend, main, make_parser, _normalize_global_options
from promptbranch_state import ConversationStateStore


def test_parser_accepts_service_options() -> None:
    parser = make_parser()
    args = parser.parse_args(
        [
            "--service-base-url",
            "http://localhost:8000",
            "--service-token",
            "secret",
            "ask",
            "hello",
        ]
    )
    assert args.service_base_url == "http://localhost:8000"
    assert args.service_token == "secret"
    assert args.command == "ask"


def test_global_options_after_subcommand_include_service_flags() -> None:
    argv = [
        "ask",
        "hello",
        "--service-base-url",
        "http://localhost:8000",
        "--service-token",
        "secret",
    ]
    normalized = _normalize_global_options(argv)
    assert normalized[:4] == [
        "--service-base-url",
        "http://localhost:8000",
        "--service-token",
        "secret",
    ]
    assert normalized[4:] == ["ask", "hello"]


def test_build_backend_uses_service_client_when_base_url_is_present() -> None:
    args = argparse.Namespace(
        service_base_url="http://localhost:8000",
        service_token="secret",
        service_timeout_seconds=123.0,
        project_url="https://chatgpt.com/g/demo/project",
        email=None,
        password=None,
        password_file=None,
        profile_dir="./.pb_profile",
        headless=False,
        use_playwright=False,
        browser_channel=None,
        enable_fedcm=False,
        keep_no_sandbox=False,
        max_retries=2,
        retry_backoff_seconds=2.0,
    )
    backend = build_backend(args)
    assert backend.__class__.__name__ == "ServiceBackend"


def test_main_can_ask_via_service_backend(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            assert base_url == "http://localhost:8000"
            assert token == "secret"
            assert timeout == 900.0

        def ask_result(self, prompt: str, **kwargs):
            assert prompt == "hello"
            assert kwargs["project_url"] == "https://chatgpt.com/g/demo/project"
            return {"answer": "world", "conversation_url": "https://chatgpt.com/g/demo/c/123"}

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main(
        [
            "--service-base-url",
            "http://localhost:8000",
            "--service-token",
            "secret",
            "--profile-dir",
            str(tmp_path),
            "--project-url",
            "https://chatgpt.com/g/demo/project",
            "ask",
            "hello",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == "world"


def test_main_json_ask_emits_full_payload_with_conversation_url(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            assert base_url == "http://localhost:8000"
            assert token == "secret"
            assert timeout == 900.0

        def ask_result(self, prompt: str, **kwargs):
            assert prompt == "hello"
            assert kwargs["project_url"] == "https://chatgpt.com/g/demo/project"
            return {"answer": {"status": "ok"}, "conversation_url": "https://chatgpt.com/g/demo/c/123"}

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main(
        [
            "--service-base-url",
            "http://localhost:8000",
            "--service-token",
            "secret",
            "--profile-dir",
            str(tmp_path),
            "--project-url",
            "https://chatgpt.com/g/demo/project",
            "ask",
            "--json",
            "hello",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["answer"] == {"status": "ok"}
    assert payload["conversation_url"] == "https://chatgpt.com/g/demo/c/123"


def test_main_can_create_project_via_service_backend(monkeypatch, capsys) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def create_project(self, name: str, **kwargs):
            assert name == "Demo"
            assert kwargs["icon"] == "folder"
            assert kwargs["color"] == "blue"
            assert kwargs["memory_mode"] == "project-only"
            return {"ok": True, "project_url": "https://chatgpt.com/g/new/project"}

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main(
        [
            "--service-base-url",
            "http://localhost:8000",
            "project-create",
            "Demo",
            "--icon",
            "folder",
            "--color",
            "blue",
            "--memory-mode",
            "project-only",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(captured.out)["project_url"] == "https://chatgpt.com/g/new/project"


def test_main_reuses_saved_project_conversation_for_follow_up_service_asks(monkeypatch, capsys, tmp_path) -> None:
    calls: list[str | None] = []
    conversation_url = "https://chatgpt.com/g/demo/c/123"

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def ask_result(self, prompt: str, **kwargs):
            calls.append(kwargs.get("project_url"))
            if prompt == "first":
                return {"answer": "one", "conversation_url": conversation_url}
            return {"answer": "two", "conversation_url": conversation_url}

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    first_exit_code = main(
        [
            "--service-base-url",
            "http://localhost:8000",
            "--profile-dir",
            str(tmp_path),
            "--project-url",
            "https://chatgpt.com/g/demo/project",
            "ask",
            "first",
        ]
    )
    second_exit_code = main(
        [
            "--service-base-url",
            "http://localhost:8000",
            "--profile-dir",
            str(tmp_path),
            "--project-url",
            "https://chatgpt.com/g/demo/project",
            "ask",
            "second",
        ]
    )

    captured = capsys.readouterr()
    assert first_exit_code == 0
    assert second_exit_code == 0
    assert calls == [
        "https://chatgpt.com/g/demo/project",
        "https://chatgpt.com/g/demo/c/123",
    ]
    assert captured.out.strip().splitlines() == ["one", "two"]


def test_main_can_ask_via_service_backend_from_env(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            assert base_url == "http://localhost:8000"
            assert token == "secret"
            assert timeout == 900.0

        def ask_result(self, prompt: str, **kwargs):
            assert prompt == "hello"
            return {"answer": "world", "conversation_url": "https://chatgpt.com/g/demo/c/123"}

    monkeypatch.setenv("CHATGPT_SERVICE_BASE_URL", "http://localhost:8000")
    monkeypatch.setenv("CHATGPT_SERVICE_TOKEN", "secret")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main(
        [
            "--profile-dir",
            str(tmp_path),
            "ask",
            "hello",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == "world"


def test_main_can_ask_via_service_backend_from_config(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            assert base_url == "http://localhost:8000"
            assert token == "secret"
            assert timeout == 123.0

        def ask_result(self, prompt: str, **kwargs):
            assert prompt == "hello"
            return {"answer": "world", "conversation_url": "https://chatgpt.com/g/demo/c/123"}

    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "service_base_url": "http://localhost:8000",
                "service_token": "secret",
                "service_timeout_seconds": 123,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.delenv("CHATGPT_SERVICE_BASE_URL", raising=False)
    monkeypatch.delenv("CHATGPT_SERVICE_TOKEN", raising=False)
    monkeypatch.delenv("CHATGPT_SERVICE_TIMEOUT_SECONDS", raising=False)
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main(
        [
            "--config",
            str(config_path),
            "--profile-dir",
            str(tmp_path),
            "ask",
            "hello",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == "world"


def test_main_can_ask_via_service_backend_from_default_config_path(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            assert base_url == "http://localhost:8000"
            assert token == "secret"
            assert timeout == 123.0

        def ask_result(self, prompt: str, **kwargs):
            assert prompt == "hello"
            return {"answer": "world", "conversation_url": "https://chatgpt.com/g/demo/c/123"}

    config_dir = tmp_path / ".config" / "chatgpt-cli"
    config_dir.mkdir(parents=True)
    (config_dir / "config.json").write_text(
        json.dumps(
            {
                "service_base_url": "http://localhost:8000",
                "service_token": "secret",
                "service_timeout_seconds": 123,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("CHATGPT_CLI_CONFIG", raising=False)
    monkeypatch.delenv("CHATGPT_SERVICE_BASE_URL", raising=False)
    monkeypatch.delenv("CHATGPT_SERVICE_TOKEN", raising=False)
    monkeypatch.delenv("CHATGPT_SERVICE_TIMEOUT_SECONDS", raising=False)
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main(
        [
            "--profile-dir",
            str(tmp_path / "profile"),
            "ask",
            "hello",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == "world"


def test_main_can_list_projects_via_service_backend(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            assert base_url == "http://localhost:8000"

        def list_projects(self, **kwargs):
            assert kwargs["project_url"] == "https://chatgpt.com/g/demo/project"
            return {
                "ok": True,
                "count": 2,
                "projects": [
                    {"name": "Alpha", "url": "https://chatgpt.com/g/demo-alpha/project", "is_current": False},
                    {"name": "Demo", "url": "https://chatgpt.com/g/demo/project", "is_current": True},
                ],
            }

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main(
        [
            "--service-base-url",
            "http://localhost:8000",
            "--profile-dir",
            str(tmp_path),
            "--project-url",
            "https://chatgpt.com/g/demo/project",
            "project-list",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Alpha	https://chatgpt.com/g/demo-alpha/project" in captured.out
    assert "* Demo	https://chatgpt.com/g/demo/project" in captured.out


def test_main_project_list_json_emits_full_payload(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_projects(self, **kwargs):
            return {
                "ok": True,
                "count": 1,
                "projects": [{"name": "Demo", "url": "https://chatgpt.com/g/demo/project", "is_current": True}],
            }

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main(
        [
            "--service-base-url",
            "http://localhost:8000",
            "--profile-dir",
            str(tmp_path),
            "project-list",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["count"] == 1
    assert payload["projects"][0]["name"] == "Demo"


def test_main_project_list_current_filters_to_current(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_projects(self, **kwargs):
            return {
                "ok": True,
                "count": 2,
                "projects": [
                    {"name": "Alpha", "url": "https://chatgpt.com/g/alpha/project", "is_current": False},
                    {"name": "Demo", "url": "https://chatgpt.com/g/demo/project", "is_current": True},
                ],
            }

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "project-list", "--current",
    ])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Demo	https://chatgpt.com/g/demo/project" in captured.out
    assert "Alpha	https://chatgpt.com/g/alpha/project" not in captured.out


def test_main_project_list_writes_global_cache(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_projects(self, **kwargs):
            return {
                "ok": True,
                "count": 2,
                "projects": [
                    {"name": "Alpha", "url": "https://chatgpt.com/g/g-p-alpha-alpha/project", "is_current": False},
                    {"name": "Demo", "url": "https://chatgpt.com/g/g-p-demo-demo/project", "is_current": True},
                ],
            }

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path / "profile-a"),
        "project-list",
    ])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Demo	https://chatgpt.com/g/g-p-demo-demo/project" in captured.out
    cache_path = tmp_path / "xdg" / "promptbranch" / "project-list-cache.json"
    assert cache_path.exists()
    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    assert payload["projects"][0]["name"] == "Demo"
    assert payload["projects"][1]["name"] == "Alpha"


def test_main_use_can_fall_back_to_global_project_cache(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_projects(self, **kwargs):
            return {
                "ok": True,
                "count": 1,
                "projects": [
                    {"name": "Demo", "url": "https://chatgpt.com/g/g-p-demo-demo/project", "is_current": True},
                ],
            }

        def resolve_project(self, name: str, **kwargs):
            return {"ok": False, "error": "not_found", "name": name}

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    profile_a = tmp_path / "profile-a"
    profile_b = tmp_path / "profile-b"

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile_a),
        "project-list",
    ])
    assert exit_code == 0
    capsys.readouterr()

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile_b),
        "use", "Demo",
    ])

    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["resolved_via"] == "global_cache"
    state_payload = json.loads((profile_b / ".promptbranch_state.json").read_text(encoding="utf-8"))
    assert state_payload["current"]["project_home_url"] == "https://chatgpt.com/g/g-p-demo-demo/project"


def test_main_use_pick_selects_project_and_updates_state(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_projects(self, **kwargs):
            return {
                "ok": True,
                "count": 2,
                "projects": [
                    {"name": "Alpha", "url": "https://chatgpt.com/g/g-p-alpha/project", "is_current": False},
                    {"name": "Demo", "url": "https://chatgpt.com/g/g-p-demo/project", "is_current": True},
                ],
            }

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)
    monkeypatch.setattr("builtins.input", lambda prompt='': "1")

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "use", "--pick", "--json",
    ])

    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["ok"] is True
    assert payload["selected_via"] == "pick"
    assert payload["project_name"] == "Alpha"
    assert payload["project_home_url"] == "https://chatgpt.com/g/g-p-alpha/project"

    state_payload = json.loads((tmp_path / ".promptbranch_state.json").read_text(encoding="utf-8"))
    assert state_payload["current"]["project_home_url"] == "https://chatgpt.com/g/g-p-alpha/project"
    assert state_payload["current"]["project_name"] == "Alpha"


def test_main_use_pick_with_filter_and_single_match_does_not_prompt(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_projects(self, **kwargs):
            return {
                "ok": True,
                "count": 2,
                "projects": [
                    {"name": "Alpha Project", "url": "https://chatgpt.com/g/g-p-alpha/project", "is_current": False},
                    {"name": "Beta Project", "url": "https://chatgpt.com/g/g-p-beta/project", "is_current": False},
                ],
            }

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    def _unexpected_input(prompt=''):
        raise AssertionError("input() should not be called for a single filtered match")

    monkeypatch.setattr("builtins.input", _unexpected_input)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "use", "Alpha", "--pick", "--json",
    ])

    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["project_name"] == "Alpha Project"


def test_main_use_without_target_or_pick_returns_usage_error(monkeypatch, capsys, tmp_path) -> None:
    exit_code = main(["--profile-dir", str(tmp_path), "use"])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert "target is required unless --pick is used" in captured.err


def test_main_version_subcommand_outputs_release(capsys) -> None:
    exit_code = main(["version"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == "promptbranch 0.0.113"


def test_main_project_source_list_json_emits_source_payload(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_project_sources(self, **kwargs):
            return {
                "ok": True,
                "count": 2,
                "sources": [
                    {"title": "architecture-process_0.1.16.zip", "subtitle": "File", "identity": "architecture-process_0.1.16.zip File"},
                    {"title": "notes.txt", "subtitle": "Document", "identity": "notes.txt Document"},
                ],
            }

    store = ConversationStateStore(str(tmp_path))
    store.remember_project("https://chatgpt.com/g/g-p-demo-project/project", project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "project-source-list", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["count"] == 2
    assert payload["sources"][0]["title"] == "architecture-process_0.1.16.zip"


def test_main_chat_list_json_emits_chat_payload(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_project_chats(self, **kwargs):
            return {
                "ok": True,
                "count": 2,
                "chats": [
                    {"id": "abc", "title": "First chat", "conversation_url": "https://chatgpt.com/g/g-p-demo-project/c/abc"},
                    {"id": "def", "title": "Second chat", "conversation_url": "https://chatgpt.com/g/g-p-demo-project/c/def"},
                ],
            }

    store = ConversationStateStore(str(tmp_path))
    store.remember_project("https://chatgpt.com/g/g-p-demo-project/project", project_name="demo-project")
    store.remember("https://chatgpt.com/g/g-p-demo-project/project", "https://chatgpt.com/g/g-p-demo-project/c/def")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "chat-list", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["count"] == 2
    assert any(item["is_current"] for item in payload["chats"])


def test_main_chat_use_by_index_updates_state(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_project_chats(self, **kwargs):
            return {
                "ok": True,
                "count": 2,
                "chats": [
                    {"id": "abc", "title": "First chat", "conversation_url": "https://chatgpt.com/g/g-p-demo-project/c/abc"},
                    {"id": "def", "title": "Second chat", "conversation_url": "https://chatgpt.com/g/g-p-demo-project/c/def"},
                ],
            }

    store = ConversationStateStore(str(tmp_path))
    store.remember_project("https://chatgpt.com/g/g-p-demo-project/project", project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "chat-use", "2", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["conversation_id"] == "def"
    assert store.snapshot()["conversation_id"] == "def"


def test_main_chat_leave_clears_only_conversation(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    store = ConversationStateStore(str(tmp_path))
    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-project/c/abc"
    store.remember_project(project_url, project_name="demo-project")
    store.remember(project_url, conversation_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "chat-leave", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["conversation_url"] is None
    snapshot = store.snapshot(project_url)
    assert snapshot["resolved_project_home_url"] == project_url
    assert snapshot["conversation_url"] is None


def test_main_chat_show_json_fetches_selected_chat(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def get_chat(self, conversation_url: str, **kwargs):
            assert conversation_url == "https://chatgpt.com/g/g-p-demo-project/c/abc"
            return {
                "ok": True,
                "conversation_id": "abc",
                "conversation_url": conversation_url,
                "title": "First chat",
                "turn_count": 1,
                "turns": [{"index": 1, "role": "user", "text": "hello"}],
            }

    store = ConversationStateStore(str(tmp_path))
    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-project/c/abc"
    store.remember_project(project_url, project_name="demo-project")
    store.remember(project_url, conversation_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "chat-show", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["conversation_id"] == "abc"
    assert payload["turns"][0]["text"] == "hello"


def test_test_suite_command_dispatches_to_runner(monkeypatch, capsys) -> None:
    async def fake_run_test_suite_async(**kwargs):
        assert kwargs['keep_project'] is True
        assert kwargs['only'] == ['project_list_debug']
        return {'ok': True, 'action': 'test_suite'}

    monkeypatch.setattr('promptbranch_cli.run_test_suite_async', fake_run_test_suite_async)

    from promptbranch_cli import main

    rc = main(['test-suite', '--keep-project', '--only', 'project_list_debug'])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['action'] == 'test_suite'


def test_main_project_source_add_file_normalizes_name_to_basename(monkeypatch, capsys, tmp_path) -> None:
    calls: dict[str, object] = {}

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def add_project_source(self, **kwargs):
            calls.update(kwargs)
            return {"ok": True, "action": "add"}

    file_path = tmp_path / "candlecast-src-0.19.5.82.2.zip"
    file_path.write_bytes(b"zip")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main(
        [
            "--service-base-url",
            "http://localhost:8000",
            "project-source-add",
            "--file",
            str(file_path),
            "--name",
            "/tmp/releases/candlecast-src-0.19.5.82.2.zip",
        ]
    )

    assert exit_code == 0
    assert calls["display_name"] == "candlecast-src-0.19.5.82.2.zip"
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True


def test_phase1_canonical_parser_accepts_ws_task_src_test_and_doctor() -> None:
    parser = make_parser()

    ws_args = parser.parse_args(["ws", "use", "Demo"])
    assert ws_args.command == "ws"
    assert ws_args.ws_command == "use"
    assert ws_args.target == "Demo"

    task_args = parser.parse_args(["task", "show", "2", "--json"])
    assert task_args.command == "task"
    assert task_args.task_command == "show"
    assert task_args.target == "2"
    assert task_args.json is True

    src_args = parser.parse_args(["src", "add", "--file", "demo.zip"])
    assert src_args.command == "src"
    assert src_args.src_command == "add"
    assert src_args.type == "file"
    assert src_args.file == "demo.zip"

    test_args = parser.parse_args(["test", "smoke", "--only", "project_list_debug"])
    assert test_args.command == "test"
    assert test_args.test_command == "smoke"
    assert test_args.only == ["project_list_debug"]

    doctor_args = parser.parse_args(["doctor", "--json"])
    assert doctor_args.command == "doctor"
    assert doctor_args.json is True


def test_phase1_ws_use_delegates_to_existing_use_flow(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def resolve_project(self, name: str, **kwargs):
            assert name == "my-project"
            return {"ok": True, "project_url": "https://chatgpt.com/g/g-p-demo-my-project/project"}

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "ws", "use", "my-project", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["current_project_home_url"] == "https://chatgpt.com/g/g-p-demo-my-project/project"

    snapshot = ConversationStateStore(str(tmp_path)).snapshot()
    assert snapshot["resolved_project_home_url"] == "https://chatgpt.com/g/g-p-demo-my-project/project"


def test_phase1_task_use_delegates_to_existing_chat_flow(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_project_chats(self, **kwargs):
            return {
                "ok": True,
                "chats": [
                    {"id": "abc", "title": "First", "conversation_url": "https://chatgpt.com/g/g-p-demo-project/c/abc"},
                    {"id": "def", "title": "Second", "conversation_url": "https://chatgpt.com/g/g-p-demo-project/c/def"},
                ],
            }

    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "task", "use", "2", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["conversation_id"] == "def"
    assert store.snapshot(project_url)["conversation_id"] == "def"


def test_phase1_src_list_delegates_to_existing_source_flow(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_project_sources(self, **kwargs):
            return {
                "ok": True,
                "sources": [
                    {"title": "notes.txt", "subtitle": "Document", "identity": "notes.txt Document"},
                ],
            }

    store = ConversationStateStore(str(tmp_path))
    store.remember_project("https://chatgpt.com/g/g-p-demo-project/project", project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "src", "list", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["count"] == 1
    assert payload["sources"][0]["title"] == "notes.txt"


def test_phase1_doctor_reports_state_without_mutating(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "doctor", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["action"] == "doctor"
    assert payload["version"] == "0.0.113"
    assert payload["checks"]["workspace_selected"] is True


def test_phase2_task_messages_list_groups_flat_transcript(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def get_chat(self, conversation_url: str, **kwargs):
            assert conversation_url == "https://chatgpt.com/g/g-p-demo-project/c/abc"
            return {
                "ok": True,
                "project_url": "https://chatgpt.com/g/g-p-demo-project/project",
                "conversation_url": conversation_url,
                "conversation_id": "abc",
                "title": "Phase 2 chat",
                "turns": [
                    {"index": 1, "id": "u1", "role": "user", "text": "first question"},
                    {"index": 2, "id": "a1", "role": "assistant", "text": "first answer"},
                    {"index": 3, "id": "u2", "role": "user", "text": "second question"},
                ],
            }

    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-project/c/abc"
    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="demo-project")
    store.remember(project_url, conversation_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "task", "messages", "list", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["action"] == "task_messages_list"
    assert payload["message_count"] == 2
    assert payload["messages"][0]["text"] == "first question"
    assert payload["messages"][0]["answer_count"] == 1
    assert payload["messages"][0]["answers"][0]["text"] == "first answer"
    assert payload["messages"][1]["answered"] is False


def test_phase2_task_message_show_selects_user_message(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def get_chat(self, conversation_url: str, **kwargs):
            return {
                "ok": True,
                "conversation_url": conversation_url,
                "conversation_id": "abc",
                "title": "Phase 2 chat",
                "turns": [
                    {"index": 1, "id": "u1", "role": "user", "text": "first question"},
                    {"index": 2, "id": "a1", "role": "assistant", "text": "first answer"},
                    {"index": 3, "id": "u2", "role": "user", "text": "second question"},
                ],
            }

    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-project/c/abc"
    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="demo-project")
    store.remember(project_url, conversation_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "task", "message", "show", "2", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["action"] == "task_message_show"
    assert payload["message"]["id"] == "u2"
    assert payload["message"]["text"] == "second question"


def test_phase2_task_message_answer_outputs_answers(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def get_chat(self, conversation_url: str, **kwargs):
            return {
                "ok": True,
                "conversation_url": conversation_url,
                "conversation_id": "abc",
                "title": "Phase 2 chat",
                "turns": [
                    {"index": 1, "id": "u1", "role": "user", "text": "first question"},
                    {"index": 2, "id": "a1", "role": "assistant", "text": "first answer"},
                    {"index": 3, "id": "a2", "role": "assistant", "text": "regenerated answer"},
                ],
            }

    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-project/c/abc"
    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="demo-project")
    store.remember(project_url, conversation_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "task", "message", "answer", "u1", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["action"] == "task_message_answer"
    assert payload["answer_count"] == 2
    assert [answer["text"] for answer in payload["answers"]] == ["first answer", "regenerated answer"]


def test_phase2_task_messages_list_accepts_raw_mapping_payload(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def get_chat(self, conversation_url: str, **kwargs):
            return {
                "ok": True,
                "conversation_url": conversation_url,
                "conversation_id": "abc",
                "title": "Raw mapping chat",
                "current_node": "a1",
                "mapping": {
                    "root": {"id": "root", "parent": None, "message": None},
                    "u1": {
                        "parent": "root",
                        "message": {
                            "author": {"role": "user"},
                            "content": {"parts": ["raw question"]},
                        },
                    },
                    "a1": {
                        "parent": "u1",
                        "message": {
                            "author": {"role": "assistant"},
                            "content": {"parts": ["raw answer"]},
                        },
                    },
                },
            }

    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-project/c/abc"
    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="demo-project")
    store.remember(project_url, conversation_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "task", "messages", "list", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["message_count"] == 1
    assert payload["messages"][0]["text"] == "raw question"
    assert payload["messages"][0]["answers"][0]["text"] == "raw answer"


def test_phase2_task_message_answer_accepts_latest_alias(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def get_chat(self, conversation_url: str, **kwargs):
            return {
                "ok": True,
                "conversation_url": conversation_url,
                "conversation_id": "abc",
                "title": "Phase 2 chat",
                "turns": [
                    {"index": 1, "id": "u1", "role": "user", "text": "first question"},
                    {"index": 2, "id": "a1", "role": "assistant", "text": "first answer"},
                    {"index": 3, "id": "u2", "role": "user", "text": "second question"},
                    {"index": 4, "id": "a2", "role": "assistant", "text": "second answer"},
                ],
            }

    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-project/c/abc"
    store = ConversationStateStore(str(tmp_path))
    store.remember_project(project_url, project_name="demo-project")
    store.remember(project_url, conversation_url, project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "task", "message", "answer", "latest", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["message"]["id"] == "u2"
    assert payload["answers"][0]["text"] == "second answer"
