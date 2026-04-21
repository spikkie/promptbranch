from __future__ import annotations

import argparse
import json

from promptbranch_cli import build_backend, main, make_parser, _normalize_global_options


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
        profile_dir="./profile",
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
    assert captured.out.strip() == "promptbranch 0.0.82"
