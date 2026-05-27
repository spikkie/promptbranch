from __future__ import annotations

import asyncio

from promptbranch_automation.automation import ChatGPTAutomation
from promptbranch_automation.service import ChatGPTAutomationService, ChatGPTAutomationSettings
from promptbranch_browser_auth.exceptions import ResponseTimeoutError


class _DummyClient:
    async def list_projects(self, *, keep_open: bool = False):
        return {"ok": True, "count": 1, "projects": [{"name": "Demo"}], "keep_open": keep_open}


def test_automation_exposes_list_projects(monkeypatch):
    dummy = _DummyClient()
    monkeypatch.setattr(ChatGPTAutomation, "client", property(lambda self: dummy))

    bot = ChatGPTAutomation(project_url="https://chatgpt.com/", email=None, password=None)
    result = asyncio.run(bot.list_projects(keep_open=True))

    assert result["ok"] is True
    assert result["count"] == 1
    assert result["keep_open"] is True


def test_service_list_projects_calls_automation(monkeypatch):
    async def fake_list_projects(self, *, keep_open: bool = False):
        return {"ok": True, "count": 2, "projects": [{"name": "A"}, {"name": "B"}], "keep_open": keep_open}

    monkeypatch.setattr(ChatGPTAutomation, "list_projects", fake_list_projects)

    svc = ChatGPTAutomationService(ChatGPTAutomationSettings(
        project_url="https://chatgpt.com/",
        email=None,
        password=None,
        profile_dir="/tmp/.pb_profile",
        headless=True,
        use_patchright=False,
    ))

    result = asyncio.run(svc.list_projects(keep_open=False))

    assert result["ok"] is True
    assert result["count"] == 2


def test_automation_exposes_debug_project_list(monkeypatch):
    class _DummyDebugClient(_DummyClient):
        async def debug_project_list(self, *, scroll_rounds: int = 12, wait_ms: int = 350, manual_pause: bool = False, keep_open: bool = False):
            return {
                "ok": True,
                "artifact_dir": "/tmp/debug-artifacts",
                "helper_collected_count": 3,
                "scroll_rounds": scroll_rounds,
                "wait_ms": wait_ms,
                "manual_pause": manual_pause,
                "keep_open": keep_open,
            }

    dummy = _DummyDebugClient()
    monkeypatch.setattr(ChatGPTAutomation, "client", property(lambda self: dummy))

    bot = ChatGPTAutomation(project_url="https://chatgpt.com/", email=None, password=None)
    result = asyncio.run(bot.debug_project_list(scroll_rounds=4, wait_ms=222, manual_pause=True, keep_open=True))

    assert result["ok"] is True
    assert result["helper_collected_count"] == 3
    assert result["scroll_rounds"] == 4
    assert result["wait_ms"] == 222
    assert result["manual_pause"] is True
    assert result["keep_open"] is True


def test_service_debug_project_list_calls_automation(monkeypatch):
    async def fake_debug_project_list(self, *, scroll_rounds: int = 12, wait_ms: int = 350, manual_pause: bool = False, keep_open: bool = False):
        return {
            "ok": True,
            "artifact_dir": "/tmp/debug-artifacts",
            "helper_collected_count": 5,
            "scroll_rounds": scroll_rounds,
            "wait_ms": wait_ms,
            "manual_pause": manual_pause,
            "keep_open": keep_open,
        }

    monkeypatch.setattr(ChatGPTAutomation, "debug_project_list", fake_debug_project_list)

    svc = ChatGPTAutomationService(ChatGPTAutomationSettings(
        project_url="https://chatgpt.com/",
        email=None,
        password=None,
        profile_dir="/tmp/.pb_profile",
        headless=True,
        use_patchright=False,
    ))

    result = asyncio.run(svc.debug_project_list(scroll_rounds=7, wait_ms=600, manual_pause=False, keep_open=False))

    assert result["ok"] is True
    assert result["helper_collected_count"] == 5
    assert result["scroll_rounds"] == 7
    assert result["wait_ms"] == 600


def test_automation_exposes_chat_methods(monkeypatch):
    class _DummyChatClient(_DummyClient):
        async def list_project_chats(self, *, keep_open: bool = False, include_history_fallback: bool = True):
            return {"ok": True, "count": 1, "chats": [{"id": "abc", "title": "Demo chat"}], "keep_open": keep_open, "include_history_fallback": include_history_fallback}

        async def get_chat(self, *, conversation_url: str, keep_open: bool = False):
            return {"ok": True, "conversation_id": "abc", "conversation_url": conversation_url, "keep_open": keep_open}

    dummy = _DummyChatClient()
    monkeypatch.setattr(ChatGPTAutomation, "client", property(lambda self: dummy))

    bot = ChatGPTAutomation(project_url="https://chatgpt.com/g/demo/project", email=None, password=None)
    list_result = asyncio.run(bot.list_project_chats(keep_open=True))
    show_result = asyncio.run(bot.get_chat(conversation_url="https://chatgpt.com/g/demo/c/abc", keep_open=False))

    assert list_result["count"] == 1
    assert show_result["conversation_id"] == "abc"


def test_service_chat_methods_call_automation(monkeypatch):
    async def fake_list_project_chats(self, *, keep_open: bool = False, include_history_fallback: bool = True):
        return {"ok": True, "count": 2, "chats": [{"id": "a"}, {"id": "b"}], "keep_open": keep_open, "include_history_fallback": include_history_fallback}

    async def fake_get_chat(self, *, conversation_url: str, keep_open: bool = False):
        return {"ok": True, "conversation_id": "abc", "conversation_url": conversation_url, "keep_open": keep_open}

    monkeypatch.setattr(ChatGPTAutomation, "list_project_chats", fake_list_project_chats)
    monkeypatch.setattr(ChatGPTAutomation, "get_chat", fake_get_chat)

    svc = ChatGPTAutomationService(ChatGPTAutomationSettings(
        project_url="https://chatgpt.com/",
        email=None,
        password=None,
        profile_dir="/tmp/.pb_profile",
        headless=True,
        use_patchright=False,
    ))

    list_result = asyncio.run(svc.list_project_chats(keep_open=False))
    show_result = asyncio.run(svc.get_chat(conversation_url="https://chatgpt.com/g/demo/c/abc", keep_open=True))

    assert list_result["count"] == 2
    assert show_result["conversation_id"] == "abc"


def test_automation_exposes_project_source_list(monkeypatch):
    class _DummySourceClient(_DummyClient):
        async def list_project_sources(self, *, keep_open: bool = False):
            return {
                "ok": True,
                "count": 2,
                "sources": [{"title": "notes.txt"}, {"title": "design.pdf"}],
                "keep_open": keep_open,
            }

    dummy = _DummySourceClient()
    monkeypatch.setattr(ChatGPTAutomation, "client", property(lambda self: dummy))

    bot = ChatGPTAutomation(project_url="https://chatgpt.com/g/demo/project", email=None, password=None)
    result = asyncio.run(bot.list_project_sources(keep_open=True))

    assert result["ok"] is True
    assert result["count"] == 2
    assert result["sources"][0]["title"] == "notes.txt"
    assert result["keep_open"] is True


def test_service_project_source_list_calls_automation(monkeypatch):
    async def fake_list_project_sources(self, *, keep_open: bool = False):
        return {
            "ok": True,
            "count": 1,
            "sources": [{"title": "architecture-process_0.1.16.zip"}],
            "keep_open": keep_open,
        }

    monkeypatch.setattr(ChatGPTAutomation, "list_project_sources", fake_list_project_sources)

    svc = ChatGPTAutomationService(ChatGPTAutomationSettings(
        project_url="https://chatgpt.com/",
        email=None,
        password=None,
        profile_dir="/tmp/.pb_profile",
        headless=True,
        use_patchright=False,
    ))

    result = asyncio.run(svc.list_project_sources(keep_open=False))

    assert result["ok"] is True
    assert result["count"] == 1
    assert result["sources"][0]["title"] == "architecture-process_0.1.16.zip"




def test_service_remembers_verified_file_source_for_next_overwrite(monkeypatch, tmp_path):
    file_path = tmp_path / "itest-file.txt"
    file_path.write_text("demo", encoding="utf-8")
    add_calls: list[dict] = []
    remove_calls: list[dict] = []

    async def fake_add_project_source(self, **kwargs):
        add_calls.append(kwargs)
        return {
            "ok": True,
            "action": "add",
            "project_url": "https://chatgpt.com/g/g-p-demo/project",
            "source_kind": "file",
            "source_match": "itest-file.txt Document",
            "source_match_requested": "itest-file.txt",
            "source_match_candidates": ["itest-file.txt", "itest-file.txt Document"],
            "persistence_verified": True,
            "already_exists": False,
            "added": True,
            "overwritten": False,
            "removed_existing": False,
        }

    async def fake_remove_project_source(self, **kwargs):
        remove_calls.append(kwargs)
        return {"ok": True, "removed_via_ui": True, "source_match": kwargs["source_name"]}

    monkeypatch.setattr(ChatGPTAutomation, "add_project_source", fake_add_project_source)
    monkeypatch.setattr(ChatGPTAutomation, "remove_project_source", fake_remove_project_source)

    svc = ChatGPTAutomationService(ChatGPTAutomationSettings(
        project_url="https://chatgpt.com/g/g-p-demo/project",
        email=None,
        password=None,
        profile_dir="/tmp/.pb_profile",
        headless=True,
        use_patchright=False,
    ))

    first = asyncio.run(svc.add_project_source(source_kind="file", file_path=str(file_path), overwrite_existing=True))
    second = asyncio.run(svc.add_project_source(source_kind="file", file_path=str(file_path), overwrite_existing=True))

    assert first["persistence_verified"] is True
    assert len(add_calls) == 2
    assert len(remove_calls) == 1
    assert remove_calls[0]["source_name"] == "itest-file.txt"
    assert remove_calls[0]["exact"] is True
    assert second["already_exists"] is True
    assert second["overwritten"] is True
    assert second["removed_existing"] is True
    assert second["overwrite_classification_source"] == "remembered_verified_before_state"
    assert second["remembered_source"]["source_match"] == "itest-file.txt Document"
    assert second["remembered_overwrite_remove_result"]["removed_via_ui"] is True


def test_service_forgets_remembered_overwrite_when_remove_cannot_verify(monkeypatch, tmp_path):
    file_path = tmp_path / "itest-file.txt"
    file_path.write_text("demo", encoding="utf-8")
    add_calls: list[dict] = []
    remove_calls: list[dict] = []

    async def fake_add_project_source(self, **kwargs):
        add_calls.append(kwargs)
        return {
            "ok": True,
            "action": "add",
            "project_url": "https://chatgpt.com/g/g-p-demo/project",
            "source_kind": "file",
            "source_match": "itest-file.txt Document",
            "source_match_requested": "itest-file.txt",
            "source_match_candidates": ["itest-file.txt", "itest-file.txt Document"],
            "persistence_verified": True,
            "already_exists": False,
            "added": True,
            "overwritten": False,
            "removed_existing": False,
        }

    async def fake_remove_project_source(self, **kwargs):
        remove_calls.append(kwargs)
        raise ResponseTimeoutError("remove did not verify")

    monkeypatch.setattr(ChatGPTAutomation, "add_project_source", fake_add_project_source)
    monkeypatch.setattr(ChatGPTAutomation, "remove_project_source", fake_remove_project_source)

    svc = ChatGPTAutomationService(ChatGPTAutomationSettings(
        project_url="https://chatgpt.com/g/g-p-demo/project",
        email=None,
        password=None,
        profile_dir="/tmp/.pb_profile",
        headless=True,
        use_patchright=False,
    ))

    first = asyncio.run(svc.add_project_source(source_kind="file", file_path=str(file_path), overwrite_existing=True))
    failed = asyncio.run(svc.add_project_source(source_kind="file", file_path=str(file_path), overwrite_existing=True))
    third = asyncio.run(svc.add_project_source(source_kind="file", file_path=str(file_path), overwrite_existing=True))

    assert first["persistence_verified"] is True
    assert failed["ok"] is False
    assert failed["status"] == "remembered_overwrite_remove_failed"
    assert failed["already_exists"] is True
    assert failed["overwritten"] is False
    assert failed["removed_existing"] is False
    assert failed["operator_review_required"] is True
    assert failed["overwrite_classification_source"] == "remembered_verified_before_state"
    assert len(remove_calls) == 1
    # The failed remembered remove must clear the memory rather than looping on
    # the same stale identity forever. The third call therefore falls back to
    # the browser client's normal add/overwrite path.
    assert third["ok"] is True
    assert len(add_calls) == 2

def test_service_remembers_recent_task_from_ask_for_task_list(monkeypatch):
    async def fake_ask_question_result(self, **kwargs):
        return {
            "answer": "TASK_MESSAGE_OK",
            "conversation_url": "https://chatgpt.com/g/g-p-demo-itest/c/chat-recent-1",
        }

    async def fake_list_project_chats(self, *, keep_open: bool = False, include_history_fallback: bool = True):
        return {
            "ok": True,
            "project_url": "https://chatgpt.com/g/g-p-demo/project",
            "count": 0,
            "chats": [],
            "source_counts": {"snorlax": 0, "dom": 0, "current_page": 0, "history": 0},
            "include_history_fallback": include_history_fallback,
        }

    monkeypatch.setattr(ChatGPTAutomation, "ask_question_result", fake_ask_question_result)
    monkeypatch.setattr(ChatGPTAutomation, "list_project_chats", fake_list_project_chats)

    svc = ChatGPTAutomationService(ChatGPTAutomationSettings(
        project_url="https://chatgpt.com/g/g-p-demo/project",
        email=None,
        password=None,
        profile_dir="/tmp/.pb_profile",
        headless=True,
        use_patchright=False,
    ))

    ask_result = asyncio.run(svc.ask_question_result(prompt="hello", retries=0))
    list_result = asyncio.run(svc.list_project_chats(keep_open=False, include_history_fallback=False))

    assert ask_result["conversation_url"].endswith("/c/chat-recent-1")
    assert list_result["count"] == 1
    assert list_result["chats"][0]["id"] == "chat-recent-1"
    assert list_result["chats"][0]["source"] == "recent_state"
    assert list_result["source_counts"]["recent_state"] == 1
    assert list_result["recent_state_fallback_used"] is True
    assert list_result["visibility_status"] == "recent_state_only"
    assert list_result["indexed_task_count"] == 0


def test_service_does_not_duplicate_recent_task_when_backend_lists_it(monkeypatch):
    async def fake_ask_question_result(self, **kwargs):
        return {
            "answer": "TASK_MESSAGE_OK",
            "conversation_url": "https://chatgpt.com/g/g-p-demo/c/chat-visible-1",
        }

    async def fake_list_project_chats(self, *, keep_open: bool = False, include_history_fallback: bool = True):
        return {
            "ok": True,
            "project_url": "https://chatgpt.com/g/g-p-demo/project",
            "count": 1,
            "chats": [{"id": "chat-visible-1", "title": "Backend listed", "conversation_url": "https://chatgpt.com/g/g-p-demo/c/chat-visible-1"}],
            "source_counts": {"snorlax": 1, "dom": 0, "current_page": 0, "history": 0},
        }

    monkeypatch.setattr(ChatGPTAutomation, "ask_question_result", fake_ask_question_result)
    monkeypatch.setattr(ChatGPTAutomation, "list_project_chats", fake_list_project_chats)

    svc = ChatGPTAutomationService(ChatGPTAutomationSettings(
        project_url="https://chatgpt.com/g/g-p-demo/project",
        email=None,
        password=None,
        profile_dir="/tmp/.pb_profile",
        headless=True,
        use_patchright=False,
    ))

    asyncio.run(svc.ask_question_result(prompt="hello", retries=0))
    list_result = asyncio.run(svc.list_project_chats(keep_open=False))

    assert list_result["count"] == 1
    assert list_result["chats"][0]["title"] == "Backend listed"
    assert list_result["source_counts"]["recent_state"] == 0
    assert list_result["visibility_status"] == "indexed"
    assert list_result["indexed_task_count"] == 1


def test_service_indexed_task_count_reports_unique_tasks_not_observation_sum() -> None:
    payload = {
        "ok": True,
        "project_url": "https://chatgpt.com/g/g-p-demo/project",
        "chats": [
            {"id": f"task-{idx}", "title": f"Task {idx}", "conversation_url": f"https://chatgpt.com/g/g-p-demo/c/task-{idx}"}
            for idx in range(20)
        ],
        "source_counts": {"snorlax": 20, "dom": 10, "current_page": 0, "history": 0, "history_detail": 0},
    }
    svc = ChatGPTAutomationService(ChatGPTAutomationSettings(
        project_url="https://chatgpt.com/g/g-p-demo/project",
        email=None,
        password=None,
        profile_dir="/tmp/.pb_profile",
        headless=True,
        use_patchright=False,
    ))

    result = svc._augment_chat_list_with_recent_state(payload)

    assert result["count"] == 20
    assert result["visibility_status"] == "indexed"
    assert result["indexed_task_count"] == 20
    assert result["indexed_observation_count"] == 30


def test_profile_scoped_lock_serializes_services_sharing_profile(monkeypatch, tmp_path):
    events: list[str] = []
    profile_dir = tmp_path / ".pb_profile"

    async def fake_ask_question_result(self, **kwargs):
        events.append("ask-start")
        await asyncio.sleep(0.05)
        events.append("ask-end")
        return {"answer": "done", "conversation_url": "https://chatgpt.com/g/g-p-one/c/a"}

    async def fake_add_project_source(self, **kwargs):
        events.append("source-add-start")
        await asyncio.sleep(0.01)
        events.append("source-add-end")
        return {"ok": True, "persistence_verified": True, "source_kind": kwargs.get("source_kind")}

    monkeypatch.setattr(ChatGPTAutomation, "ask_question_result", fake_ask_question_result)
    monkeypatch.setattr(ChatGPTAutomation, "add_project_source", fake_add_project_source)

    svc_a = ChatGPTAutomationService(ChatGPTAutomationSettings(
        project_url="https://chatgpt.com/g/g-p-one/project",
        email=None,
        password=None,
        profile_dir=str(profile_dir),
        headless=True,
        use_patchright=False,
    ))
    svc_b = ChatGPTAutomationService(ChatGPTAutomationSettings(
        project_url="https://chatgpt.com/g/g-p-two/project",
        email=None,
        password=None,
        profile_dir=str(profile_dir),
        headless=True,
        use_patchright=False,
    ))

    async def run_concurrently() -> None:
        ask_task = asyncio.create_task(svc_a.ask_question_result(prompt="hello", retries=0))
        while "ask-start" not in events:
            await asyncio.sleep(0)
        add_task = asyncio.create_task(svc_b.add_project_source(source_kind="text", value="notes"))
        await asyncio.gather(ask_task, add_task)

    asyncio.run(run_concurrently())

    assert events == ["ask-start", "ask-end", "source-add-start", "source-add-end"]
    assert (profile_dir / ".promptbranch-browser-profile.lock").exists()


def test_profile_scoped_lock_reports_busy_before_client_timeout(monkeypatch, tmp_path):
    from promptbranch_browser_auth.exceptions import BrowserProfileBusyError

    events: list[str] = []
    profile_dir = tmp_path / ".pb_profile"

    async def fake_ask_question_result(self, **kwargs):
        events.append("ask-start")
        await asyncio.sleep(0.08)
        events.append("ask-end")
        return {"answer": "done", "conversation_url": "https://chatgpt.com/g/g-p-one/c/a"}

    async def fake_list_project_sources(self, **kwargs):
        events.append("source-list-start")
        return {"ok": True, "sources": []}

    monkeypatch.setattr(ChatGPTAutomation, "ask_question_result", fake_ask_question_result)
    monkeypatch.setattr(ChatGPTAutomation, "list_project_sources", fake_list_project_sources)

    svc_a = ChatGPTAutomationService(ChatGPTAutomationSettings(
        project_url="https://chatgpt.com/g/g-p-one/project",
        email=None,
        password=None,
        profile_dir=str(profile_dir),
        headless=True,
        use_patchright=False,
        profile_lock_wait_seconds=0.01,
    ))
    svc_b = ChatGPTAutomationService(ChatGPTAutomationSettings(
        project_url="https://chatgpt.com/g/g-p-two/project",
        email=None,
        password=None,
        profile_dir=str(profile_dir),
        headless=True,
        use_patchright=False,
        profile_lock_wait_seconds=0.01,
    ))

    async def run_contention() -> BrowserProfileBusyError:
        ask_task = asyncio.create_task(svc_a.ask_question_result(prompt="hello", retries=0))
        while "ask-start" not in events:
            await asyncio.sleep(0)
        try:
            await svc_b.list_project_sources()
        except BrowserProfileBusyError as exc:
            await ask_task
            return exc
        await ask_task
        raise AssertionError("expected browser profile busy classification")

    exc = asyncio.run(run_contention())
    payload = exc.to_payload()
    assert payload["status"] == "browser_profile_busy"
    assert payload["operation"] == "list_project_sources"
    assert payload["active_operation"] == "ask_question"
    assert payload["timeout_layer"] == "browser_profile_lock"
    assert "source-list-start" not in events


def test_browser_status_reports_active_operation_and_profile_available(monkeypatch, tmp_path):
    profile_dir = tmp_path / ".pb_profile"

    async def fake_ask_question_result(self, **kwargs):
        await asyncio.sleep(0.03)
        return {"answer": "done", "conversation_url": "https://chatgpt.com/g/g-p-one/c/a"}

    monkeypatch.setattr(ChatGPTAutomation, "ask_question_result", fake_ask_question_result)

    svc = ChatGPTAutomationService(ChatGPTAutomationSettings(
        project_url="https://chatgpt.com/g/g-p-one/project",
        email=None,
        password=None,
        profile_dir=str(profile_dir),
        headless=True,
        use_patchright=False,
    ))

    async def run_status_checks():
        task = asyncio.create_task(svc.ask_question_result(prompt="hello", retries=0))
        while svc.browser_status().get("active_operation") != "ask_question":
            await asyncio.sleep(0)
        busy = svc.browser_status()
        await task
        available = svc.browser_status()
        return busy, available

    busy, available = asyncio.run(run_status_checks())
    assert busy["status"] == "busy"
    assert busy["active_operation"] == "ask_question"
    assert busy["queue_enabled"] is False
    assert available["status"] == "available"


def test_profile_lock_wait_override_allows_waiting_operation(monkeypatch, tmp_path):
    events: list[str] = []
    profile_dir = tmp_path / ".pb_profile"

    async def fake_ask_question_result(self, **kwargs):
        events.append("ask-start")
        await asyncio.sleep(0.03)
        events.append("ask-end")
        return {"answer": "done", "conversation_url": "https://chatgpt.com/g/g-p-one/c/a"}

    async def fake_add_project_source(self, **kwargs):
        events.append("source-add-start")
        return {"ok": True, "persistence_verified": True}

    monkeypatch.setattr(ChatGPTAutomation, "ask_question_result", fake_ask_question_result)
    monkeypatch.setattr(ChatGPTAutomation, "add_project_source", fake_add_project_source)

    svc_a = ChatGPTAutomationService(ChatGPTAutomationSettings(
        project_url="https://chatgpt.com/g/g-p-one/project",
        email=None,
        password=None,
        profile_dir=str(profile_dir),
        headless=True,
        use_patchright=False,
        profile_lock_wait_seconds=0.001,
    ))
    svc_b = ChatGPTAutomationService(ChatGPTAutomationSettings(
        project_url="https://chatgpt.com/g/g-p-two/project",
        email=None,
        password=None,
        profile_dir=str(profile_dir),
        headless=True,
        use_patchright=False,
        profile_lock_wait_seconds=0.001,
    ))

    async def run_contention():
        ask_task = asyncio.create_task(svc_a.ask_question_result(prompt="hello", retries=0))
        while "ask-start" not in events:
            await asyncio.sleep(0)
        result = await svc_b.add_project_source(source_kind="text", value="notes", profile_lock_wait_seconds=0.2)
        await ask_task
        return result

    result = asyncio.run(run_contention())
    assert result["ok"] is True
    assert events == ["ask-start", "ask-end", "source-add-start"]
