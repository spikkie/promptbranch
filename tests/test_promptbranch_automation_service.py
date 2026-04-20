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
        profile_dir="/tmp/profile",
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
        profile_dir="/tmp/profile",
        headless=True,
        use_patchright=False,
    ))

    result = asyncio.run(svc.debug_project_list(scroll_rounds=7, wait_ms=600, manual_pause=False, keep_open=False))

    assert result["ok"] is True
    assert result["helper_collected_count"] == 5
    assert result["scroll_rounds"] == 7
    assert result["wait_ms"] == 600
