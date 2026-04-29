from __future__ import annotations

import asyncio

from promptbranch_automation.automation import ChatGPTAutomation
from promptbranch_automation.service import ChatGPTAutomationService, ChatGPTAutomationSettings


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
