from __future__ import annotations

import argparse
import asyncio
import json
import zipfile
import pytest
from pathlib import Path


@pytest.fixture(autouse=True)
def _isolate_cli_defaults(monkeypatch, tmp_path) -> None:
    """Keep tests hermetic when a developer has Promptbranch defaults configured locally."""
    monkeypatch.setenv("CHATGPT_CLI_CONFIG", str(tmp_path / "missing-cli-config.json"))
    monkeypatch.delenv("CHATGPT_SERVICE_TIMEOUT_SECONDS", raising=False)

from promptbranch_cli import build_backend, main, make_parser, _normalize_global_options, _chat_list_payload, _verify_project_source_upload_change, cmd_artifact_adopt
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
    assert captured.out.strip() == "promptbranch 0.0.200"


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

def test_main_chat_use_by_index_prefers_lightweight_task_list(monkeypatch, capsys, tmp_path) -> None:
    calls: list[bool] = []

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_project_chats(self, **kwargs):
            calls.append(bool(kwargs.get("include_history_fallback")))
            return {
                "ok": True,
                "count": 4,
                "chats": [
                    {"id": "a", "title": "One", "conversation_url": "https://chatgpt.com/g/g-p-demo-project/c/a"},
                    {"id": "b", "title": "Two", "conversation_url": "https://chatgpt.com/g/g-p-demo-project/c/b"},
                    {"id": "c", "title": "Three", "conversation_url": "https://chatgpt.com/g/g-p-demo-project/c/c"},
                    {"id": "d", "title": "Four", "conversation_url": "https://chatgpt.com/g/g-p-demo-project/c/d"},
                ],
            }

    store = ConversationStateStore(str(tmp_path))
    store.remember_project("https://chatgpt.com/g/g-p-demo-project/project", project_name="demo-project")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path),
        "chat-use", "4", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["conversation_id"] == "d"
    assert calls == [False]


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
        assert kwargs['profile'] == 'browser'
        return {'ok': True, 'action': 'test_suite'}

    monkeypatch.setattr('promptbranch_cli.run_test_suite_async', fake_run_test_suite_async)

    from promptbranch_cli import main

    rc = main(['test-suite', '--keep-project', '--only', 'project_list_debug'])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['action'] == 'test_suite'


def test_test_suite_full_profile_dispatches_to_runner(monkeypatch, capsys) -> None:
    async def fake_run_test_suite_async(**kwargs):
        assert kwargs['profile'] == 'full'
        assert kwargs['path'] == '.'
        assert kwargs['package_zip'] == 'release.zip'
        return {'ok': True, 'action': 'test_suite', 'profile': 'full'}

    monkeypatch.setattr('promptbranch_cli.run_test_suite_async', fake_run_test_suite_async)

    from promptbranch_cli import main

    rc = main(['test-suite', '--profile', 'full', '--path', '.', '--package-zip', 'release.zip'])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['profile'] == 'full'


def test_canonical_test_profile_shortcut_dispatches_to_runner(monkeypatch, capsys) -> None:
    async def fake_run_test_suite_async(**kwargs):
        assert kwargs['profile'] == 'agent'
        assert kwargs['path'] == '.'
        assert kwargs['package_zip'] == 'release.zip'
        return {'ok': True, 'action': 'test_suite', 'profile': 'agent'}

    monkeypatch.setattr('promptbranch_cli.run_test_suite_async', fake_run_test_suite_async)

    from promptbranch_cli import main

    rc = main(['test', 'agent', '--path', '.', '--package-zip', 'release.zip', '--json'])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['profile'] == 'agent'


def test_src_add_positional_file_delegates_as_file_source(monkeypatch, capsys, tmp_path) -> None:
    calls: dict[str, object] = {}

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def add_project_source(self, **kwargs):
            calls.update(kwargs)
            return {"ok": True, "action": "add"}

    file_path = tmp_path / "my_gitlab_0.0.4.zip"
    file_path.write_bytes(b"zip")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main(["--service-base-url", "http://localhost:8000", "src", "add", str(file_path)])

    assert exit_code == 0
    assert calls["source_kind"] == "file"
    assert calls["file_path"] == str(file_path)
    assert calls["display_name"] == "my_gitlab_0.0.4.zip"
    assert calls["overwrite_existing"] is True
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True


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
    assert calls["overwrite_existing"] is True
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
    assert src_args.no_overwrite is False

    src_no_overwrite_args = parser.parse_args(["src", "add", "--file", "demo.zip", "--no-overwrite"])
    assert src_no_overwrite_args.no_overwrite is True

    positional_src_args = parser.parse_args(["src", "add", "demo.zip"])
    assert positional_src_args.command == "src"
    assert positional_src_args.src_command == "add"
    assert positional_src_args.type == "file"
    assert positional_src_args.file_path == "demo.zip"
    assert positional_src_args.file is None

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
    assert payload["version"] == "0.0.200"
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


def test_chat_list_payload_includes_current_task_from_state_when_backend_empty() -> None:
    chats, payload = _chat_list_payload(
        {"ok": True, "count": 0, "chats": []},
        current_conversation_url="https://chatgpt.com/g/g-p-demo/c/chat-current-1",
    )

    assert payload["count"] == 1
    assert chats[0]["id"] == "chat-current-1"
    assert chats[0]["is_current"] is True
    assert chats[0]["source"] == "current_state"


def test_phase3_parser_accepts_src_sync_and_artifact_commands() -> None:
    parser = make_parser()

    sync_args = parser.parse_args(["src", "sync", ".", "--no-upload", "--dry-run", "--json"])
    assert sync_args.command == "src"
    assert sync_args.src_command == "sync"
    assert sync_args.path == "."
    assert sync_args.no_upload is True
    assert sync_args.dry_run is True

    upload_args = parser.parse_args(["src", "sync", ".", "--upload", "--confirm-upload", "--json"])
    assert upload_args.upload is True
    assert upload_args.confirm_upload is True

    plan_args = parser.parse_args(["src", "sync", ".", "--plan", "--json"])
    assert plan_args.dry_run is True

    current_args = parser.parse_args(["artifact", "current", "--json"])
    assert current_args.command == "artifact"
    assert current_args.artifact_command == "current"

    adopt_args = parser.parse_args(["artifact", "adopt", "chatgpt_claudecode_workflow_v1.2.3.zip", "--from-project-source", "--json"])
    assert adopt_args.command == "artifact"
    assert adopt_args.artifact_command == "adopt"
    assert adopt_args.artifact == "chatgpt_claudecode_workflow_v1.2.3.zip"
    assert adopt_args.from_project_source is True

    release_args = parser.parse_args(["artifact", "release", ".", "--filename", "demo.zip", "--json"])
    assert release_args.command == "artifact"
    assert release_args.artifact_command == "release"
    assert release_args.filename == "demo.zip"

    verify_args = parser.parse_args(["artifact", "verify", "demo.zip", "--json"])
    assert verify_args.command == "artifact"
    assert verify_args.artifact_command == "verify"
    assert verify_args.path == "demo.zip"




class _FakeArtifactAdoptBackend:
    def __init__(self, profile: Path, project_url: str, sources: list[dict[str, object]]) -> None:
        self.store = ConversationStateStore(profile)
        self.project_url = project_url
        self.sources = sources
        self.list_calls = 0
        self.store.remember_project(project_url, project_name="Demo")

    def state_snapshot(self) -> dict[str, object]:
        return self.store.snapshot(self.project_url)

    async def list_project_sources(self, *, keep_open: bool = False) -> dict[str, object]:
        self.list_calls += 1
        return {"ok": True, "status": "verified", "sources": self.sources}


def _write_test_release_zip(path: Path, version: str) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("VERSION", version + "\n")
        archive.writestr("README.md", "demo\n")


def test_artifact_adopt_existing_project_source_updates_registry_and_state(capsys, tmp_path) -> None:
    filename = "chatgpt_claudecode_workflow_v1.2.3.zip"
    zip_path = tmp_path / filename
    _write_test_release_zip(zip_path, "v1.2.3")
    profile = tmp_path / "profile"
    project_url = "https://chatgpt.com/g/g-p-demo/project"
    backend = _FakeArtifactAdoptBackend(profile, project_url, [{"title": filename, "id": "src_1"}])
    args = argparse.Namespace(
        artifact=filename,
        from_project_source=True,
        local_path=str(zip_path),
        keep_open=False,
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_adopt(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "adopted"
    assert payload["source_verified"] is True
    assert payload["project_source_mutated"] is False
    assert payload["artifact_registry_updated"] is True
    assert payload["state_artifact_updated"] is True
    assert payload["state_source_updated"] is True
    assert payload["artifact_ref"] == filename
    assert payload["artifact_version"] == "v1.2.3"
    assert payload["source_ref"] == filename
    assert payload["source_version"] == "v1.2.3"
    assert payload["checks"]["registry_current_matches_artifact"] is True
    assert payload["after_snapshot"]["state"]["artifact_ref"] == filename
    registry_payload = json.loads((profile / "promptbranch_artifacts.json").read_text(encoding="utf-8"))
    assert registry_payload["artifacts"][0]["filename"] == filename


def test_artifact_adopt_requires_exactly_one_project_source(capsys, tmp_path) -> None:
    filename = "chatgpt_claudecode_workflow_v1.2.3.zip"
    zip_path = tmp_path / filename
    _write_test_release_zip(zip_path, "v1.2.3")
    profile = tmp_path / "profile"
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [])
    args = argparse.Namespace(
        artifact=filename,
        from_project_source=True,
        local_path=str(zip_path),
        keep_open=False,
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_adopt(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["status"] == "project_source_match_count_invalid"
    assert payload["artifact_registry_updated"] if "artifact_registry_updated" in payload else True
    assert not (profile / "promptbranch_artifacts.json").exists()


def test_artifact_adopt_rejects_zip_version_mismatch(capsys, tmp_path) -> None:
    filename = "chatgpt_claudecode_workflow_v1.2.3.zip"
    zip_path = tmp_path / filename
    _write_test_release_zip(zip_path, "v1.2.4")
    profile = tmp_path / "profile"
    backend = _FakeArtifactAdoptBackend(profile, "https://chatgpt.com/g/g-p-demo/project", [{"title": filename}])
    args = argparse.Namespace(
        artifact=filename,
        from_project_source=True,
        local_path=str(zip_path),
        keep_open=False,
        json=True,
        profile_dir=str(profile),
    )

    exit_code = asyncio.run(cmd_artifact_adopt(backend, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["status"] == "version_mismatch"
    assert payload["zip_version"] == "v1.2.4"
    assert not (profile / "promptbranch_artifacts.json").exists()


def test_phase3_src_sync_dry_run_does_not_package_or_record_artifact(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.3\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "src", "sync", str(repo), "--dry-run", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "planned"
    assert payload["dry_run"] is True
    assert payload["mutating_actions_executed"] is False
    assert payload["artifact"]["filename"] == "repo_v1.2.3.zip"
    assert payload["included_count"] == 2
    assert payload["prechecks"]["repo_snapshot_plan_built"] is True
    assert payload["transaction_id"]
    assert payload["before_snapshot"]["repo"]["included_count"] == 2
    assert payload["before_snapshot"]["artifact_registry"]["exists"] is False
    assert payload["collateral_checks"]["would_overwrite_artifact_file"] is False
    assert payload["transaction_plan"]["verification_plan"]["after"]
    assert not Path(payload["artifact"]["path"]).exists()
    assert not (profile / "promptbranch_artifacts.json").exists()




def test_phase3_src_sync_requires_explicit_mode_before_mutation(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.3\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "src", "sync", str(repo), "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["status"] == "sync_mode_required"
    assert payload["mutating_actions_executed"] is False
    assert payload["project_source_mutated"] is False
    assert not (profile / "artifacts" / "repo_v1.2.3.zip").exists()
    assert "--no-upload" in payload["next_commands"]["local_package"]
    assert "--upload" in payload["next_commands"]["upload_preflight"]


def test_phase3_src_sync_upload_requires_confirmation(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.3\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "src", "sync", str(repo), "--upload", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["status"] == "upload_confirmation_required"
    assert payload["upload_requested"] is True
    assert payload["confirm_upload"] is False
    assert payload["mutating_actions_executed"] is False
    assert payload["project_source_mutated"] is False
    assert payload["confirmation"]["required"] is True
    assert "--confirm-upload" in payload["confirmation"]["confirm_command"]
    assert not (profile / "artifacts" / "repo_v1.2.3.zip").exists()



def test_phase3_src_sync_confirm_upload_requires_transaction_id(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.3\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "src", "sync", str(repo), "--upload", "--confirm-upload", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["status"] == "upload_transaction_id_required"
    assert payload["mutating_actions_executed"] is False
    assert payload["project_source_mutated"] is False
    assert payload["transaction_id"]
    assert "--confirm-transaction-id" in payload["confirmation"]["confirm_command"]
    assert not (profile / "artifacts" / "repo_v1.2.3.zip").exists()


def test_phase3_src_sync_confirm_upload_rejects_transaction_id_mismatch(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.3\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "src", "sync", str(repo), "--upload", "--confirm-upload", "--confirm-transaction-id", "bad-token", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["status"] == "upload_transaction_id_mismatch"
    assert payload["provided_transaction_id"] == "bad-token"
    assert payload["mutating_actions_executed"] is False
    assert payload["project_source_mutated"] is False
    assert not (profile / "artifacts" / "repo_v1.2.3.zip").exists()




def test_phase3_src_sync_upload_transaction_id_changes_when_repo_content_changes(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.3\n", encoding="utf-8")
    source = repo / "main.py"
    source.write_text("print('before')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    project_url = "https://chatgpt.com/g/g-p-demo/project"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    first_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--json",
    ])
    first = json.loads(capsys.readouterr().out)
    assert first_code == 2
    first_transaction_id = first["transaction_id"]
    first_fingerprint = first["preflight"]["before_snapshot"]["repo"]["content_fingerprint"]["sha256"]

    source.write_text("print('after')\n", encoding="utf-8")

    second_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--json",
    ])
    second = json.loads(capsys.readouterr().out)
    assert second_code == 2
    assert second["transaction_id"] != first_transaction_id
    assert second["preflight"]["before_snapshot"]["repo"]["content_fingerprint"]["sha256"] != first_fingerprint

    stale_confirm_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--confirm-upload",
        "--confirm-transaction-id", first_transaction_id, "--json",
    ])
    stale = json.loads(capsys.readouterr().out)
    assert stale_confirm_code == 2
    assert stale["status"] == "upload_transaction_id_mismatch"
    assert stale["provided_transaction_id"] == first_transaction_id
    assert stale["transaction_id"] == second["transaction_id"]
    assert stale["mutating_actions_executed"] is False
    assert stale["project_source_mutated"] is False
    assert not (profile / "artifacts" / "repo_v1.2.3.zip").exists()

def test_phase3_src_sync_confirm_upload_with_transaction_id_executes_guarded_upload(monkeypatch, capsys, tmp_path) -> None:
    calls: list[dict[str, object]] = []

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_project_sources(self, **kwargs):
            if calls:
                return {"ok": True, "action": "source_list", "sources": [{"title": "repo_v1.2.3.zip"}]}
            return {"ok": True, "action": "source_list", "sources": []}

        def add_project_source(self, **kwargs):
            calls.append(kwargs)
            return {"ok": True, "action": "source_add", "status": "verified"}

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.3\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    project_url = "https://chatgpt.com/g/g-p-demo/project"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    preflight_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--json",
    ])
    preflight_payload = json.loads(capsys.readouterr().out)
    assert preflight_code == 2
    transaction_id = preflight_payload["transaction_id"]

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--confirm-upload", "--confirm-transaction-id", transaction_id, "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "uploaded"
    assert payload["project_source_mutated"] is True
    assert payload["transaction_id"] == transaction_id
    assert calls[0]["source_kind"] == "file"
    assert calls[0]["display_name"] == "repo_v1.2.3.zip"




def test_phase3_source_upload_verification_marks_service_error_with_expected_source_as_ambiguous() -> None:
    payload = _verify_project_source_upload_change(
        before_result={"ok": True, "action": "source_list", "sources": []},
        after_result={"ok": True, "action": "source_list", "sources": [{"title": "repo_v1.2.8.zip"}]},
        upload_result={"ok": False, "action": "source_add", "status": "service_error", "error": "504 gateway timeout"},
        expected_filename="repo_v1.2.8.zip",
    )

    assert payload["ok"] is False
    assert payload["status"] == "upload_ambiguous"
    assert payload["operator_review_required"] is True
    assert payload["ambiguity_reason"] == "upload_result_failed_but_expected_source_present_after"
    assert payload["checks"]["upload_result_ok"] is False
    assert payload["checks"]["expected_source_present_after"] is True
    assert payload["collateral_change_detected"] is False

def test_phase3_src_sync_confirm_upload_failure_does_not_advance_registry_or_state(monkeypatch, capsys, tmp_path) -> None:
    calls: list[dict[str, object]] = []

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_project_sources(self, **kwargs):
            return {"ok": True, "action": "source_list", "sources": []}

        def add_project_source(self, **kwargs):
            calls.append(kwargs)
            return {"ok": False, "action": "source_add", "status": "verification_failed"}

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.4\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    project_url = "https://chatgpt.com/g/g-p-demo/project"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    preflight_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--json",
    ])
    preflight_payload = json.loads(capsys.readouterr().out)
    assert preflight_code == 2
    transaction_id = preflight_payload["transaction_id"]

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--confirm-upload", "--confirm-transaction-id", transaction_id, "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["status"] == "upload_failed"
    assert payload["project_source_mutated"] is False
    assert payload["artifact_registry_updated"] is False
    assert payload["state_source_updated"] is False
    assert payload["upload_verification"]["registry_update_deferred_until_upload_verified"] is True
    assert Path(payload["artifact"]["path"]).is_file()
    assert not (profile / "promptbranch_artifacts.json").exists()
    assert calls[0]["display_name"] == "repo_v1.2.4.zip"


def test_phase3_src_sync_confirm_upload_requires_after_source_list_match(monkeypatch, capsys, tmp_path) -> None:
    calls: list[dict[str, object]] = []

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_project_sources(self, **kwargs):
            return {"ok": True, "action": "source_list", "sources": []}

        def add_project_source(self, **kwargs):
            calls.append(kwargs)
            return {"ok": True, "action": "source_add", "status": "verified"}

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.5\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    project_url = "https://chatgpt.com/g/g-p-demo/project"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    preflight_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--json",
    ])
    preflight_payload = json.loads(capsys.readouterr().out)
    assert preflight_code == 2
    transaction_id = preflight_payload["transaction_id"]

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--confirm-upload", "--confirm-transaction-id", transaction_id, "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["status"] == "upload_failed"
    assert payload["upload_verification"]["source_list_verification"]["status"] == "source_upload_not_verified"
    assert payload["upload_verification"]["source_list_verification"]["checks"]["expected_source_present_after"] is False
    assert payload["artifact_registry_updated"] is False
    assert payload["state_source_updated"] is False
    assert calls[0]["display_name"] == "repo_v1.2.5.zip"


def test_phase3_src_sync_confirm_upload_rejects_collateral_source_removal(monkeypatch, capsys, tmp_path) -> None:
    calls: list[dict[str, object]] = []

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_project_sources(self, **kwargs):
            if calls:
                return {"ok": True, "action": "source_list", "sources": [{"title": "repo_v1.2.6.zip"}]}
            return {"ok": True, "action": "source_list", "sources": [{"title": "keep-me.txt"}]}

        def add_project_source(self, **kwargs):
            calls.append(kwargs)
            return {"ok": True, "action": "source_add", "status": "verified"}

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.6\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    project_url = "https://chatgpt.com/g/g-p-demo/project"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    preflight_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--json",
    ])
    preflight_payload = json.loads(capsys.readouterr().out)
    assert preflight_code == 2
    transaction_id = preflight_payload["transaction_id"]

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--confirm-upload", "--confirm-transaction-id", transaction_id, "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    verification = payload["upload_verification"]["source_list_verification"]
    assert verification["checks"]["expected_source_present_after"] is True
    assert verification["checks"]["collateral_sources_removed"] is True
    assert verification["collateral_change_detected"] is True
    assert payload["artifact_registry_updated"] is False
    assert payload["state_source_updated"] is False

def test_phase3_src_sync_rejects_conflicting_upload_modes(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.3\n", encoding="utf-8")
    profile = tmp_path / "profile"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "src", "sync", str(repo), "--no-upload", "--upload", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["status"] == "conflicting_sync_modes"
    assert payload["mutating_actions_executed"] is False

def test_phase3_src_sync_dry_run_reports_artifact_collisions(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.3\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    artifact_dir = profile / "artifacts"
    artifact_dir.mkdir(parents=True)
    existing = artifact_dir / "repo_v1.2.3.zip"
    existing.write_bytes(b"old")

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "src", "sync", str(repo), "--dry-run", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "planned"
    assert payload["collateral_checks"]["output_path_exists"] is True
    assert payload["collateral_checks"]["would_overwrite_artifact_file"] is True
    assert existing.read_bytes() == b"old"

def test_phase3_src_sync_no_upload_packages_and_records_artifact(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.0.0\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path / "profile"),
        "src", "sync", str(repo), "--no-upload", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "verified_packaged"
    assert payload["no_upload"] is True
    assert payload["project_source_mutated"] is False
    assert payload["artifact"]["filename"] == "repo_v1.0.0.zip"
    assert Path(payload["artifact"]["path"]).is_file()
    assert payload["local_verification"]["ok"] is True
    assert payload["local_verification"]["checks"]["zip_exists"] is True
    assert payload["local_verification"]["checks"]["registry_contains_artifact"] is True
    assert payload["local_verification"]["checks"]["project_source_mutated"] is False



def test_phase3_src_sync_no_upload_refuses_collision_without_force(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.0.0\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    artifact_dir = profile / "artifacts"
    artifact_dir.mkdir(parents=True)
    existing = artifact_dir / "repo_v1.0.0.zip"
    existing.write_bytes(b"old")

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "src", "sync", str(repo), "--no-upload", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["status"] == "local_artifact_collision"
    assert payload["mutating_actions_executed"] is False
    assert payload["collisions"]["output_path_exists"] is True
    assert existing.read_bytes() == b"old"



def test_phase3_src_sync_upload_preflight_collision_confirm_command_includes_force(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.0.0\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    artifact_dir = profile / "artifacts"
    artifact_dir.mkdir(parents=True)
    existing = artifact_dir / "repo_v1.0.0.zip"
    existing.write_bytes(b"old")
    project_url = "https://chatgpt.com/g/g-p-demo/project"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["status"] == "upload_confirmation_required"
    assert payload["confirmation"]["force_required"] is True
    assert "--force" in payload["confirmation"]["confirm_command"]
    assert any("local artifact collision" in warning for warning in payload["warnings"])
    assert existing.read_bytes() == b"old"


def test_phase3_src_sync_confirm_upload_collision_returns_force_confirmation(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.0.0\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    artifact_dir = profile / "artifacts"
    artifact_dir.mkdir(parents=True)
    existing = artifact_dir / "repo_v1.0.0.zip"
    existing.write_bytes(b"old")
    project_url = "https://chatgpt.com/g/g-p-demo/project"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    preflight_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--json",
    ])
    preflight_payload = json.loads(capsys.readouterr().out)
    assert preflight_code == 2
    transaction_id = preflight_payload["transaction_id"]

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--confirm-upload", "--confirm-transaction-id", transaction_id, "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["status"] == "local_artifact_collision"
    assert payload["mutating_actions_executed"] is False
    assert payload["confirmation"]["force_required"] is True
    assert "--force" in payload["confirmation"]["confirm_command"]
    assert existing.read_bytes() == b"old"

def test_phase3_src_sync_no_upload_force_overwrites_and_verifies(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.0.0\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    artifact_dir = profile / "artifacts"
    artifact_dir.mkdir(parents=True)
    existing = artifact_dir / "repo_v1.0.0.zip"
    existing.write_bytes(b"old")

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "src", "sync", str(repo), "--no-upload", "--force", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "verified_packaged"
    assert payload["local_verification"]["ok"] is True
    assert existing.read_bytes() != b"old"

def test_phase3_artifact_release_current_and_verify(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.0.0\n", encoding="utf-8")
    (repo / "README.md").write_text("# demo\n", encoding="utf-8")

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)
    profile = tmp_path / "profile"

    release_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "artifact", "release", str(repo), "--json",
    ])
    release_payload = json.loads(capsys.readouterr().out)
    assert release_code == 0
    assert release_payload["ok"] is True
    artifact_path = release_payload["artifact"]["path"]

    current_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "artifact", "current", "--json",
    ])
    current_payload = json.loads(capsys.readouterr().out)
    assert current_code == 0
    assert current_payload["registry_current"]["path"] == artifact_path
    assert current_payload["runtime"]["version"].startswith("v0.0.")
    assert current_payload["baseline_roles"]["adopted_artifact_ref"] is None
    assert current_payload["baseline_roles"]["adopted_source_ref"] is None
    assert current_payload["baseline_roles"]["registry_current_ref"] == Path(artifact_path).name
    assert current_payload["baseline_roles"]["registry_current_version"] == "v1.0.0"
    assert current_payload["baseline_roles"]["code_matches_adopted_source"] is False
    assert current_payload["consistency"]["registry_current_matches_state_artifact"] is False
    assert current_payload["consistency"]["state_source_matches_state_artifact"] is False
    assert current_payload["consistency"]["code_version_matches_state_source"] is False

    verify_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "artifact", "verify", artifact_path, "--json",
    ])
    verify_payload = json.loads(capsys.readouterr().out)
    assert verify_code == 0
    assert verify_payload["ok"] is True
    assert verify_payload["wrapper_folder"] is None


def test_task_list_payload_reports_unique_indexed_task_count_not_source_observation_sum() -> None:
    chats, payload = _chat_list_payload(
        {
            "ok": True,
            "source_counts": {"snorlax": 20, "dom": 10, "current_page": 0, "history": 0, "history_detail": 0},
            "chats": [
                {"id": f"task-{idx}", "title": f"Task {idx}", "conversation_url": f"https://chatgpt.com/g/g-p-demo/c/task-{idx}"}
                for idx in range(20)
            ],
        }
    )

    assert len(chats) == 20
    assert payload["visibility_status"] == "indexed"
    assert payload["indexed_task_count"] == 20
    assert payload["indexed_observation_count"] == 30


def test_task_list_payload_recomputes_stale_service_visibility_diagnostics() -> None:
    chats, payload = _chat_list_payload(
        {
            "ok": True,
            "visibility_status": "missing",
            "indexed_observation_count": 20,
            "recent_state_count": 99,
            "source_counts": {"snorlax": 20, "project_endpoint": 25, "dom": 0, "current_page": 0, "history": 0, "history_detail": 0},
            "chats": [
                {
                    "id": f"task-{idx}",
                    "title": f"Task {idx}",
                    "conversation_url": f"https://chatgpt.com/g/g-p-demo/c/task-{idx}",
                    "source": "project_endpoint",
                }
                for idx in range(25)
            ],
        }
    )

    assert len(chats) == 25
    assert payload["visibility_status"] == "indexed"
    assert payload["indexed_task_count"] == 25
    assert payload["indexed_observation_count"] == 45
    assert payload["recent_state_count"] == 0


def test_main_ask_combines_prompt_file_and_repeatable_attachments(monkeypatch, capsys, tmp_path) -> None:
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("extra context", encoding="utf-8")
    first = tmp_path / "one.log"
    second = tmp_path / "two.log"
    first.write_text("one", encoding="utf-8")
    second.write_text("two", encoding="utf-8")
    captured_kwargs: dict[str, object] = {}

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def ask_result(self, prompt: str, **kwargs):
            captured_kwargs.update(kwargs)
            assert prompt == "review\n\nextra context"
            return {"answer": "ok", "conversation_url": "https://chatgpt.com/g/demo/c/123"}

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(tmp_path / "profile"),
        "--project-url", "https://chatgpt.com/g/demo/project",
        "ask", "review",
        "--prompt-file", str(prompt_file),
        "--attach", str(first),
        "--attachment", str(second),
    ])

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "ok"
    assert captured_kwargs["attachment_paths"] == [str(first), str(second)]
    assert captured_kwargs["file_path"] is None


def test_test_full_uses_rate_limit_safe_defaults(monkeypatch, capsys) -> None:
    async def fake_run_test_suite_async(**kwargs):
        assert kwargs["profile"] == "full"
        assert kwargs["rate_limit_safe"] is True
        assert kwargs["step_delay_seconds"] == 15.0
        assert kwargs["post_ask_delay_seconds"] == 45.0
        assert kwargs["task_list_visible_poll_min_seconds"] == 30.0
        assert kwargs["task_list_visible_poll_max_seconds"] == 60.0
        assert kwargs["task_list_visible_max_attempts"] == 3
        return {"ok": True, "action": "test_suite", "profile": "full"}

    monkeypatch.setattr("promptbranch_cli.run_test_suite_async", fake_run_test_suite_async)

    from promptbranch_cli import main

    rc = main(["test", "full", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "full"


def test_test_full_can_disable_rate_limit_safe_defaults(monkeypatch, capsys) -> None:
    async def fake_run_test_suite_async(**kwargs):
        assert kwargs["profile"] == "full"
        assert kwargs["rate_limit_safe"] is False
        assert kwargs["step_delay_seconds"] == 8.0
        assert kwargs["post_ask_delay_seconds"] == 20.0
        assert kwargs["task_list_visible_max_attempts"] == 4
        return {"ok": True, "action": "test_suite", "profile": "full"}

    monkeypatch.setattr("promptbranch_cli.run_test_suite_async", fake_run_test_suite_async)

    from promptbranch_cli import main

    rc = main(["test", "full", "--no-rate-limit-safe", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["profile"] == "full"



def test_test_status_command_dispatches(monkeypatch, capsys) -> None:
    def fake_status(**kwargs):
        assert kwargs["path"] == "."
        assert kwargs["log"] == "pb_test.full.log"
        assert kwargs["service_log"] == "service.log"
        return {"ok": True, "action": "test_status", "status": "verified"}

    monkeypatch.setattr("promptbranch_cli.build_test_status", fake_status)

    from promptbranch_cli import main

    rc = main(["test", "status", "--log", "pb_test.full.log", "--service-log", "service.log", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "test_status"
    assert payload["status"] == "verified"

def test_test_import_smoke_command_dispatches(monkeypatch, capsys) -> None:
    def fake_import_smoke(**kwargs):
        assert kwargs["repo_path"] == "."
        return {"ok": True, "action": "package_import_smoke", "status": "verified"}

    monkeypatch.setattr("promptbranch_cli.package_import_smoke", fake_import_smoke)

    from promptbranch_cli import main

    rc = main(["test", "import-smoke", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "package_import_smoke"
    assert payload["status"] == "verified"


def test_test_report_command_emits_summary(capsys, tmp_path) -> None:
    log_path = tmp_path / "pb_test.full.log"
    log_path.write_text(
        "noise before\n"
        + json.dumps({
            "ok": True,
            "action": "test_suite",
            "profile": "full",
            "browser": {"ok": True, "steps": [{"name": "login", "ok": True}]},
            "agent": {
                "ok": True,
                "version": "v0.0.200",
                "steps": [
                    {"name": "package_hygiene", "ok": True, "payload": {"status": "verified", "bad_entries": [], "wrapper_folder": False}}
                ],
            },
            "rate_limit_telemetry": {"rate_limit_modal_detected": False, "conversation_history_429_seen": False},
            "safety": {"write_tools_blocked": True, "model_has_execution_authority": False, "source_or_artifact_mutation_allowed": False},
        }, indent=2)
        + "\nnoise after\n",
        encoding="utf-8",
    )

    from promptbranch_cli import main

    rc = main(["test", "report", str(log_path), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "test_report"
    assert payload["ok"] is True
    assert payload["suite"]["profile"] == "full"
    assert payload["suite"]["browser"]["step_count"] == 1
    assert payload["suite"]["agent"]["step_count"] == 1
    assert payload["suite"]["package_hygiene"]["status"] == "verified"

def test_json_command_stdout_is_parseable_without_debug_noise(monkeypatch, capsys, tmp_path) -> None:
    def fake_status(**kwargs):
        return {"ok": True, "action": "test_status", "status": "verified"}

    monkeypatch.setattr("promptbranch_cli.build_test_status", fake_status)
    monkeypatch.setenv("CHATGPT_DEBUG", "1")

    from promptbranch_cli import main

    rc = main(["test", "status", "--json"])
    captured = capsys.readouterr()
    assert rc == 0
    payload = json.loads(captured.out)
    assert payload["action"] == "test_status"
    assert "Using selector" not in captured.out
    assert "Using selector" not in captured.err


def test_json_command_debug_flag_keeps_logging_on_stderr(monkeypatch, capsys) -> None:
    def fake_status(**kwargs):
        return {"ok": True, "action": "test_status", "status": "verified"}

    monkeypatch.setattr("promptbranch_cli.build_test_status", fake_status)

    from promptbranch_cli import main

    rc = main(["--debug", "test", "status", "--json"])
    captured = capsys.readouterr()
    assert rc == 0
    payload = json.loads(captured.out)
    assert payload["status"] == "verified"
    assert captured.out.lstrip().startswith("{")






def test_src_add_service_error_returns_structured_json_without_traceback(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def add_project_source(self, **kwargs):
            raise RuntimeError("504 error for POST http://localhost:8000/v1/project-sources: Could not find the remove/delete action for the selected project source")

    file_path = tmp_path / "architecture-process_0.1.29.zip"
    file_path.write_bytes(b"zip")
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main(["--service-base-url", "http://localhost:8000", "src", "add", str(file_path)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["status"] == "overwrite_remove_failed"
    assert payload["project_source_mutated"] is False
    assert payload["operator_review_required"] is True
    assert "Traceback" not in captured.out
    assert "Traceback" not in captured.err

def test_phase3_src_sync_confirm_upload_service_error_with_expected_source_is_ambiguous(monkeypatch, capsys, tmp_path) -> None:
    calls: list[dict[str, object]] = []

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_project_sources(self, **kwargs):
            if calls:
                return {"ok": True, "action": "source_list", "sources": [{"title": "repo_v1.2.8.zip"}]}
            return {"ok": True, "action": "source_list", "sources": []}

        def add_project_source(self, **kwargs):
            calls.append(kwargs)
            raise RuntimeError("504 error for POST http://localhost:8000/v1/project-sources: Could not find the remove/delete action for the selected project source")

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.8\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    project_url = "https://chatgpt.com/g/g-p-demo/project"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    preflight_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--json",
    ])
    preflight_payload = json.loads(capsys.readouterr().out)
    assert preflight_code == 2
    transaction_id = preflight_payload["transaction_id"]

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--confirm-upload", "--confirm-transaction-id", transaction_id, "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["status"] == "upload_ambiguous"
    assert payload["project_source_mutated"] is False
    assert payload["project_source_mutation"] == "ambiguous"
    assert payload["operator_review_required"] is True
    assert payload["artifact_registry_updated"] is False
    assert payload["state_artifact_updated"] is False
    assert payload["state_source_updated"] is False
    assert payload["upload_verification"]["status"] == "upload_ambiguous"
    assert payload["upload_verification"]["operator_review_required"] is True
    assert payload["upload_verification"]["source_list_verification"]["status"] == "upload_ambiguous"
    assert payload["upload_verification"]["source_list_verification"]["ambiguity_reason"] == "upload_result_failed_but_expected_source_present_after"
    assert payload["upload_verification"]["source_list_verification"]["checks"]["expected_source_present_after"] is True
    assert payload["upload_verification"]["source_list_verification"]["collateral_change_detected"] is False
    assert Path(payload["artifact"]["path"]).is_file()
    assert not (profile / "promptbranch_artifacts.json").exists()
    assert calls[0]["display_name"] == "repo_v1.2.8.zip"

def test_phase3_src_sync_confirm_upload_service_error_returns_structured_failure(monkeypatch, capsys, tmp_path) -> None:
    calls: list[dict[str, object]] = []

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_project_sources(self, **kwargs):
            return {"ok": True, "action": "source_list", "sources": []}

        def add_project_source(self, **kwargs):
            calls.append(kwargs)
            raise RuntimeError("504 error for POST http://localhost:8000/v1/project-sources: Could not find the remove/delete action for the selected project source")

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.7\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    project_url = "https://chatgpt.com/g/g-p-demo/project"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    preflight_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--json",
    ])
    preflight_payload = json.loads(capsys.readouterr().out)
    assert preflight_code == 2
    transaction_id = preflight_payload["transaction_id"]

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "src", "sync", str(repo), "--upload", "--confirm-upload", "--confirm-transaction-id", transaction_id, "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["status"] == "upload_failed"
    assert payload["project_source_mutated"] is False
    assert payload["artifact_registry_updated"] is False
    assert payload["state_source_updated"] is False
    assert payload["upload_result"]["ok"] is False
    assert payload["upload_result"]["action"] == "source_add"
    assert payload["upload_result"]["status"] == "service_error"
    assert "remove/delete action" in payload["upload_result"]["error"]
    assert payload["upload_verification"]["registry_update_deferred_until_upload_verified"] is True
    assert Path(payload["artifact"]["path"]).is_file()
    assert not (profile / "promptbranch_artifacts.json").exists()
    assert calls[0]["display_name"] == "repo_v1.2.7.zip"


def test_v185_parser_accepts_artifact_release_source_sync_transaction_flags() -> None:
    parser = make_parser()
    args = parser.parse_args([
        "artifact", "release", ".", "--sync-source", "--upload", "--confirm-upload",
        "--confirm-transaction-id", "abc123", "--force", "--json",
    ])

    assert args.command == "artifact"
    assert args.artifact_command == "release"
    assert args.sync_source is True
    assert args.upload is True
    assert args.confirm_upload is True
    assert args.confirm_transaction_id == "abc123"
    assert args.force is True
    assert args.json is True


def test_v185_artifact_release_source_sync_upload_preflight_uses_artifact_confirm_command(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.3\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    project_url = "https://chatgpt.com/g/g-p-demo/project"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "artifact", "release", str(repo), "--sync-source", "--upload", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["action"] == "artifact_release"
    assert payload["status"] == "planned"
    assert payload["source_sync_status"] == "upload_confirmation_required"
    assert payload["release_workflow"] == "artifact_release_source_sync_v1"
    assert payload["mutating_actions_executed"] is False
    assert payload["project_source_mutated"] is False
    assert payload["confirmation"]["required"] is True
    assert "pb artifact release" in payload["confirmation"]["confirm_command"]
    assert "--sync-source" in payload["confirmation"]["confirm_command"]
    assert "--confirm-upload" in payload["confirmation"]["confirm_command"]
    assert "source_sync_confirm_command" not in payload["confirmation"]
    assert payload["confirmation"]["operator_instruction"].startswith("Run this top-level artifact release")
    assert payload["operator_instruction"].startswith("Run confirmation.confirm_command exactly")
    assert "confirm_command" not in payload["source_sync"]["confirmation"]
    assert payload["source_sync"]["confirmation"]["confirm_command_redacted"] is True
    assert "pb src sync" not in json.dumps(payload["confirmation"])
    assert not (profile / "artifacts" / "repo_v1.2.3.zip").exists()


def test_v185_artifact_release_source_sync_no_upload_packages_with_clear_status(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.4\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "artifact", "release", str(repo), "--sync-source", "--no-upload", "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["action"] == "artifact_release"
    assert payload["status"] == "packaged"
    assert payload["source_sync_status"] == "verified_packaged"
    assert payload["artifact_registry_updated"] is True
    assert payload["state_source_updated"] is False
    assert payload["project_source_mutated"] is False
    assert Path(payload["artifact"]["path"]).is_file()
    assert payload["source_sync"]["local_verification"]["status"] == "verified"


def test_v185_artifact_release_source_sync_confirm_upload_advances_state_only_after_verified_upload(monkeypatch, capsys, tmp_path) -> None:
    calls: list[dict[str, object]] = []

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def list_project_sources(self, **kwargs):
            if calls:
                return {"ok": True, "action": "source_list", "sources": [{"title": "repo_v1.2.5.zip"}]}
            return {"ok": True, "action": "source_list", "sources": []}

        def add_project_source(self, **kwargs):
            calls.append(kwargs)
            return {"ok": True, "action": "source_add", "status": "verified"}

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.5\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    project_url = "https://chatgpt.com/g/g-p-demo/project"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    preflight_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "artifact", "release", str(repo), "--sync-source", "--upload", "--json",
    ])
    preflight = json.loads(capsys.readouterr().out)
    assert preflight_code == 2

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "artifact", "release", str(repo), "--sync-source", "--upload", "--confirm-upload",
        "--confirm-transaction-id", preflight["transaction_id"], "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["action"] == "artifact_release"
    assert payload["status"] == "uploaded"
    assert payload["source_sync_status"] == "uploaded"
    assert payload["project_source_mutated"] is True
    assert payload["artifact_registry_updated"] is True
    assert payload["state_artifact_updated"] is True
    assert payload["state_source_updated"] is True
    assert payload["upload_verification"]["status"] == "verified"
    assert calls[0]["display_name"] == "repo_v1.2.5.zip"



def test_v188_artifact_release_redacts_nested_source_sync_confirm_command() -> None:
    from promptbranch_cli import _rewrite_source_sync_payload_for_artifact_release

    payload = {
        "ok": False,
        "action": "src_sync",
        "status": "upload_confirmation_required",
        "transaction_id": "tx123",
        "confirmation": {
            "required": True,
            "confirm_command": "pb src sync /repo --upload --confirm-upload --confirm-transaction-id tx123 --json",
            "force_required": False,
        },
    }

    rewritten = _rewrite_source_sync_payload_for_artifact_release(payload, repo_path=Path("/repo"))

    assert rewritten["action"] == "artifact_release"
    assert rewritten["status"] == "planned"
    assert rewritten["confirmation"]["confirm_command"].startswith("pb artifact release")
    assert "pb src sync" not in rewritten["confirmation"]["confirm_command"]
    assert "source_sync_confirm_command" not in rewritten["confirmation"]
    assert "confirm_command" not in rewritten["source_sync"]["confirmation"]
    assert rewritten["source_sync"]["confirmation"]["confirm_command_redacted"] is True


def test_v188_artifact_release_confirm_command_includes_force_when_source_sync_requires_force() -> None:
    from promptbranch_cli import _rewrite_source_sync_payload_for_artifact_release

    payload = {
        "ok": False,
        "action": "src_sync",
        "status": "upload_confirmation_required",
        "transaction_id": "tx-force",
        "confirmation": {
            "required": True,
            "force_required": True,
            "confirm_command": "pb src sync /repo --upload --confirm-upload --confirm-transaction-id tx-force --force --json",
        },
    }

    rewritten = _rewrite_source_sync_payload_for_artifact_release(payload, repo_path=Path("/repo"))

    command = rewritten["confirmation"]["confirm_command"]
    assert command.startswith("pb artifact release")
    assert "--force" in command
    assert "pb src sync" not in command
    assert "confirm_command" not in rewritten["source_sync"]["confirmation"]
    assert rewritten["source_sync"]["confirmation"]["confirm_command_redacted"] is True


def test_v188_artifact_release_wrapper_maps_success_to_top_level_uploaded() -> None:
    from promptbranch_cli import _rewrite_source_sync_payload_for_artifact_release

    payload = {
        "ok": True,
        "action": "src_sync",
        "status": "uploaded",
        "project_source_mutated": True,
        "artifact_registry_updated": True,
        "state_artifact_updated": True,
        "state_source_updated": True,
        "upload_verification": {"ok": True, "status": "verified"},
    }

    rewritten = _rewrite_source_sync_payload_for_artifact_release(payload, repo_path=Path("/repo"))

    assert rewritten["action"] == "artifact_release"
    assert rewritten["status"] == "uploaded"
    assert rewritten["source_sync_status"] == "uploaded"
    assert rewritten["source_sync_action"] == "src_sync"
    assert rewritten["artifact_registry_updated"] is True
    assert rewritten["state_artifact_updated"] is True
    assert rewritten["state_source_updated"] is True
    assert rewritten["source_sync"]["status"] == "uploaded"


def test_v188_artifact_release_wrapper_maps_ambiguous_without_advancing_state() -> None:
    from promptbranch_cli import _rewrite_source_sync_payload_for_artifact_release

    payload = {
        "ok": False,
        "action": "src_sync",
        "status": "upload_ambiguous",
        "operator_review_required": True,
        "artifact_registry_updated": False,
        "state_artifact_updated": False,
        "state_source_updated": False,
        "upload_verification": {"ok": False, "status": "upload_ambiguous"},
    }

    rewritten = _rewrite_source_sync_payload_for_artifact_release(payload, repo_path=Path("/repo"))

    assert rewritten["action"] == "artifact_release"
    assert rewritten["status"] == "upload_ambiguous"
    assert rewritten["source_sync_status"] == "upload_ambiguous"
    assert rewritten["operator_review_required"] is True
    assert rewritten["artifact_registry_updated"] is False
    assert rewritten["state_source_updated"] is False


def test_v189_artifact_release_print_confirm_command_outputs_only_top_level_command(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.9\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    project_url = "https://chatgpt.com/g/g-p-demo/project"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "artifact", "release", str(repo), "--sync-source", "--upload", "--print-confirm-command",
    ])

    output = capsys.readouterr().out.strip()
    assert exit_code == 0
    assert output.startswith("pb artifact release ")
    assert "--sync-source" in output
    assert "--confirm-upload" in output
    assert "--confirm-transaction-id" in output
    assert "pb src sync" not in output
    assert "{" not in output


def test_v189_artifact_release_print_confirm_command_includes_force_when_required(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v1.2.10\n", encoding="utf-8")
    (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
    profile = tmp_path / "profile"
    project_url = "https://chatgpt.com/g/g-p-demo/project"

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    first_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "artifact", "release", str(repo), "--sync-source", "--no-upload", "--json",
    ])
    _ = capsys.readouterr()
    assert first_code == 0

    exit_code = main([
        "--service-base-url", "http://localhost:8000",
        "--profile-dir", str(profile),
        "--project-url", project_url,
        "artifact", "release", str(repo), "--sync-source", "--upload", "--print-confirm-command",
    ])

    output = capsys.readouterr().out.strip()
    assert exit_code == 0
    assert output.startswith("pb artifact release ")
    assert "--force" in output
    assert "pb src sync" not in output
