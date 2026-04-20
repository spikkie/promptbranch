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
