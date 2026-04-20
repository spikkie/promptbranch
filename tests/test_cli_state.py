from __future__ import annotations

import json

from chatgpt_cli import main, make_parser
from chatgpt_state import ConversationStateStore


def test_parser_accepts_state_prompt_and_state_clear() -> None:
    parser = make_parser()
    assert parser.parse_args(["state"]).command == "state"
    assert parser.parse_args(["prompt"]).command == "prompt"
    assert parser.parse_args(["state-clear"]).command == "state-clear"
    assert parser.parse_args(["use", "Demo"]).command == "use"
    assert parser.parse_args(["completion", "bash"]).command == "completion"


def test_main_prompt_uses_saved_state(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    store = ConversationStateStore(str(tmp_path))
    store.remember_project("https://chatgpt.com/g/g-p-demo-my-project/project", project_name="my-project")
    store.remember(
        "https://chatgpt.com/g/g-p-demo-my-project/project",
        "https://chatgpt.com/g/g-p-demo-my-project/c/12345678-1234-1234-1234-1234567890ab",
        project_name="my-project",
    )

    monkeypatch.setattr("chatgpt_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main(
        [
            "--service-base-url",
            "http://localhost:8000",
            "--profile-dir",
            str(tmp_path),
            "prompt",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == "promptbranch:my-project#12345678"


def test_main_state_clear_removes_saved_context(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    store = ConversationStateStore(str(tmp_path))
    store.remember_project("https://chatgpt.com/g/g-p-demo-my-project/project", project_name="my-project")

    monkeypatch.setattr("chatgpt_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main(
        [
            "--service-base-url",
            "http://localhost:8000",
            "--profile-dir",
            str(tmp_path),
            "state-clear",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(captured.out)["cleared"] is True
    snapshot = store.snapshot()
    assert snapshot["has_current"] is False
    assert snapshot["current_project_home_url"] is None


def test_project_source_remove_uses_saved_current_project_when_project_url_is_default(monkeypatch, capsys, tmp_path) -> None:
    calls: list[str | None] = []

    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def remove_project_source(self, source_name: str, **kwargs):
            assert source_name == "Notes"
            calls.append(kwargs.get("project_url"))
            return {"ok": True, "removed": source_name}

    store = ConversationStateStore(str(tmp_path))
    store.remember_project("https://chatgpt.com/g/g-p-demo-my-project/project", project_name="my-project")

    monkeypatch.setattr("chatgpt_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main(
        [
            "--service-base-url",
            "http://localhost:8000",
            "--profile-dir",
            str(tmp_path),
            "project-source-remove",
            "Notes",
            "--exact",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(captured.out)["removed"] == "Notes"
    assert calls == ["https://chatgpt.com/g/g-p-demo-my-project/project"]


def test_main_use_by_project_name_updates_current_state(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

        def resolve_project(self, name: str, **kwargs):
            assert name == "my-project"
            return {"ok": True, "project_url": "https://chatgpt.com/g/g-p-demo-my-project/project"}

    monkeypatch.setattr("chatgpt_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url",
        "http://localhost:8000",
        "--profile-dir",
        str(tmp_path),
        "use",
        "my-project",
    ])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["action"] == "use"

    store = ConversationStateStore(str(tmp_path))
    snapshot = store.snapshot()
    assert snapshot["resolved_project_home_url"] == "https://chatgpt.com/g/g-p-demo-my-project/project"
    assert snapshot["project_name"] == "my-project"


def test_main_use_by_conversation_url_sets_current_chat(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    monkeypatch.setattr("chatgpt_cli.ChatGPTServiceClient", FakeServiceClient)

    conversation_url = "https://chatgpt.com/g/g-p-demo-my-project/c/12345678-1234-1234-1234-1234567890ab"
    exit_code = main([
        "--service-base-url",
        "http://localhost:8000",
        "--profile-dir",
        str(tmp_path),
        "use",
        conversation_url,
        "--json",
    ])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["conversation_url"] == conversation_url
    assert payload["conversation_id"] == "12345678-1234-1234-1234-1234567890ab"


def test_main_completion_emits_bash_script(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    monkeypatch.setattr("chatgpt_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url",
        "http://localhost:8000",
        "--profile-dir",
        str(tmp_path),
        "completion",
        "bash",
    ])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "complete -F _promptbranch_complete promptbranch" in captured.out



def test_main_completion_honors_chatgpt_alias(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    monkeypatch.setattr("chatgpt_cli.ChatGPTServiceClient", FakeServiceClient)
    monkeypatch.setattr("sys.argv", ["chatgpt", "completion", "bash"])

    exit_code = main([
        "--service-base-url",
        "http://localhost:8000",
        "--profile-dir",
        str(tmp_path),
        "completion",
        "bash",
    ])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "complete -F _chatgpt_complete chatgpt" in captured.out


def test_main_prompt_honors_chatgpt_alias(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    store = ConversationStateStore(str(tmp_path))
    store.remember_project("https://chatgpt.com/g/g-p-demo-my-project/project", project_name="my-project")

    monkeypatch.setattr("chatgpt_cli.ChatGPTServiceClient", FakeServiceClient)
    monkeypatch.setattr("sys.argv", ["chatgpt", "prompt"])

    exit_code = main([
        "--service-base-url",
        "http://localhost:8000",
        "--profile-dir",
        str(tmp_path),
        "prompt",
    ])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == "chatgpt:my-project"
