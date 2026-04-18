from __future__ import annotations

import argparse
import json

from chatgpt_cli import build_backend, main, make_parser, _normalize_global_options


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


def test_main_can_ask_via_service_backend(monkeypatch, capsys) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 300.0) -> None:
            assert base_url == "http://localhost:8000"
            assert token == "secret"
            assert timeout == 300.0

        def ask(self, prompt: str, **kwargs):
            assert prompt == "hello"
            assert kwargs["project_url"] == "https://chatgpt.com/g/demo/project"
            return "world"

    monkeypatch.setattr("chatgpt_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main(
        [
            "--service-base-url",
            "http://localhost:8000",
            "--service-token",
            "secret",
            "--project-url",
            "https://chatgpt.com/g/demo/project",
            "ask",
            "hello",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == "world"


def test_main_can_create_project_via_service_backend(monkeypatch, capsys) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 300.0) -> None:
            pass

        def create_project(self, name: str, **kwargs):
            assert name == "Demo"
            assert kwargs["icon"] == "folder"
            assert kwargs["color"] == "blue"
            assert kwargs["memory_mode"] == "project-only"
            return {"ok": True, "project_url": "https://chatgpt.com/g/new/project"}

    monkeypatch.setattr("chatgpt_cli.ChatGPTServiceClient", FakeServiceClient)

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
