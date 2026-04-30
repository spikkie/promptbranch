from __future__ import annotations

import json

from promptbranch_cli import main, make_parser
from promptbranch_state import ConversationStateStore, resolve_profile_dir


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

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

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

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

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

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

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

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

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


def test_main_use_by_bare_project_url_updates_current_state(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main([
        "--service-base-url",
        "http://localhost:8000",
        "--profile-dir",
        str(tmp_path),
        "use",
        "https://chatgpt.com/g/g-p-demo-my-project",
    ])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["project_home_url"] == "https://chatgpt.com/g/g-p-demo-my-project/project"
    assert payload["project_name"] == "my-project"

    store = ConversationStateStore(str(tmp_path))
    snapshot = store.snapshot()
    assert snapshot["resolved_project_home_url"] == "https://chatgpt.com/g/g-p-demo-my-project/project"
    assert snapshot["project_name"] == "my-project"


def test_main_use_by_conversation_url_sets_current_chat(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

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

    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

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





def test_forget_conversation_preserves_project_state(tmp_path) -> None:
    store = ConversationStateStore(str(tmp_path))
    project_url = "https://chatgpt.com/g/g-p-demo-my-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-my-project/c/12345678-1234-1234-1234-1234567890ab"
    store.remember_project(project_url, project_name="my-project")
    store.remember(project_url, conversation_url, project_name="my-project")

    store.forget_conversation(project_url)

    snapshot = store.snapshot(project_url)
    assert snapshot["resolved_project_home_url"] == project_url
    assert snapshot["conversation_url"] is None
    assert snapshot["project_name"] == "my-project"



def test_resolve_profile_dir_prefers_nearest_hidden_profile(tmp_path) -> None:
    repo = tmp_path / "repo"
    nested = repo / "sub" / "deeper"
    outer = repo / ".pb_profile"
    inner = repo / "sub" / ".pb_profile"
    outer.mkdir(parents=True)
    inner.mkdir(parents=True)
    nested.mkdir(parents=True)

    resolved = resolve_profile_dir(cwd=str(nested))

    assert resolved == inner.resolve()


def test_resolve_profile_dir_inherits_hidden_profile_from_parent(tmp_path) -> None:
    repo = tmp_path / "repo"
    nested = repo / "sub" / "deeper"
    profile = repo / ".pb_profile"
    profile.mkdir(parents=True)
    nested.mkdir(parents=True)

    resolved = resolve_profile_dir(cwd=str(nested))

    assert resolved == profile.resolve()




def test_resolve_profile_dir_ignores_visible_legacy_profile_dirs(tmp_path) -> None:
    repo = tmp_path / "repo"
    nested = repo / "sub" / "deeper"
    legacy = repo / "profile"
    legacy.mkdir(parents=True)
    nested.mkdir(parents=True)

    resolved = resolve_profile_dir(cwd=str(nested))

    assert resolved == (nested / ".pb_profile").resolve()

def test_main_uses_inherited_hidden_profile_by_default(monkeypatch, capsys, tmp_path) -> None:
    class FakeServiceClient:
        def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 900.0) -> None:
            pass

    repo = tmp_path / "repo"
    worktree = repo / "pkg" / "feature"
    profile = repo / ".pb_profile"
    profile.mkdir(parents=True)
    worktree.mkdir(parents=True)

    monkeypatch.chdir(worktree)
    monkeypatch.setattr("promptbranch_cli.ChatGPTServiceClient", FakeServiceClient)

    exit_code = main(["--service-base-url", "http://localhost:8000", "state"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert f"state_file={str((profile / '.promptbranch_state.json').resolve())}" in captured.out


def test_task_list_cache_round_trips_and_preserves_through_remember(tmp_path: Path) -> None:
    store = ConversationStateStore(str(tmp_path / ".pb_profile"))
    project_url = "https://chatgpt.com/g/g-p-demo-project/project"
    conversation_url = "https://chatgpt.com/g/g-p-demo-project/c/abc12345-1234-1234-1234-123456789abc"

    store.remember_project(project_url, project_name="Demo")
    store.remember_task_list(project_url, [
        {
            "id": "abc12345-1234-1234-1234-123456789abc",
            "title": "Cached task",
            "conversation_url": conversation_url,
            "source": "snorlax",
        }
    ])

    cached = store.task_list_cache(project_url, max_age_seconds=900)
    assert len(cached) == 1
    assert cached[0]["title"] == "Cached task"

    store.remember(project_url, conversation_url, project_name="Demo")
    cached_after_remember = store.task_list_cache(project_url, max_age_seconds=900)
    assert len(cached_after_remember) == 1
    assert cached_after_remember[0]["conversation_url"] == conversation_url
