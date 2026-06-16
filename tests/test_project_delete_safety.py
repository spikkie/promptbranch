from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from promptbranch_automation.service import ChatGPTAutomationService, ChatGPTAutomationSettings
from promptbranch_browser_auth import ChatGPTBrowserClient, ChatGPTBrowserConfig
from promptbranch_container_api import app
from promptbranch_project_delete_safety import (
    PROJECT_DELETE_DISABLED_STATUS,
    is_project_delete_disabled_payload,
    project_delete_disabled_result,
)


def test_project_delete_disabled_payload_is_machine_checkable() -> None:
    payload = project_delete_disabled_result(
        project_url="https://chatgpt.com/g/g-p-demo/project",
        project_name="promptbranch",
        blocked_at_layer="unit_test",
    )

    assert payload["ok"] is False
    assert payload["status"] == PROJECT_DELETE_DISABLED_STATUS
    assert payload["error_type"] == PROJECT_DELETE_DISABLED_STATUS
    assert payload["destructive_action_executed"] is False
    assert payload["release_blocking"] is True
    assert payload["delete_policy"] == "frozen_until_secure_delete_protocol"
    assert payload["blocked_at_layer"] == "unit_test"
    assert is_project_delete_disabled_payload(payload) is True


def test_projects_remove_endpoint_is_frozen_before_service_resolution(monkeypatch) -> None:
    def forbidden_service_resolution(project_url):  # pragma: no cover - should not be reached
        raise AssertionError("remove endpoint must not resolve or call the browser service")

    monkeypatch.setattr("promptbranch_container_api._service_for", forbidden_service_resolution)
    client = TestClient(app)

    response = client.post(
        "/v1/projects/remove",
        json={
            "project_url": "https://chatgpt.com/g/g-p-demo/project",
            "project_name": "promptbranch",
            "keep_open": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert payload["status"] == PROJECT_DELETE_DISABLED_STATUS
    assert payload["blocked_at_layer"] == "container_api"
    assert payload["project_url"] == "https://chatgpt.com/g/g-p-demo/project"
    assert payload["project_name"] == "promptbranch"
    assert payload["destructive_action_executed"] is False


def test_automation_service_remove_project_is_frozen_before_bot_creation(monkeypatch) -> None:
    settings = ChatGPTAutomationSettings(
        project_url="https://chatgpt.com/g/g-p-demo/project",
        email=None,
        password=None,
        profile_dir="/tmp/.pb_profile",
        headless=True,
        use_patchright=False,
    )
    service = ChatGPTAutomationService(settings)

    def forbidden_build_bot():  # pragma: no cover - should not be reached
        raise AssertionError("remove_project must not create a browser automation bot")

    monkeypatch.setattr(service, "_build_bot", forbidden_build_bot)

    payload = asyncio.run(service.remove_project(project_name="promptbranch"))

    assert payload["ok"] is False
    assert payload["status"] == PROJECT_DELETE_DISABLED_STATUS
    assert payload["blocked_at_layer"] == "automation_service"
    assert payload["project_url"] == "https://chatgpt.com/g/g-p-demo/project"
    assert payload["project_name"] == "promptbranch"
    assert payload["destructive_action_executed"] is False


def test_browser_client_remove_project_is_frozen_before_browser_context(tmp_path, monkeypatch) -> None:
    config = ChatGPTBrowserConfig(
        project_url="https://chatgpt.com/g/g-p-demo/project",
        profile_dir=str(tmp_path / "profile"),
        headless=True,
        debug=False,
        save_trace=False,
        save_html=False,
        save_screenshot=False,
    )
    client = ChatGPTBrowserClient(config)

    async def forbidden_run_with_context(*_args, **_kwargs):  # pragma: no cover - should not be reached
        raise AssertionError("remove_project must not launch a browser context")

    monkeypatch.setattr(client, "_run_with_context", forbidden_run_with_context)

    payload = asyncio.run(client.remove_project(project_name="promptbranch"))

    assert payload["ok"] is False
    assert payload["status"] == PROJECT_DELETE_DISABLED_STATUS
    assert payload["blocked_at_layer"] == "browser_client"
    assert payload["project_url"] == "https://chatgpt.com/g/g-p-demo/project"
    assert payload["project_name"] == "promptbranch"
    assert payload["destructive_action_executed"] is False


def test_full_integration_cleanup_accepts_delete_frozen_payload() -> None:
    from promptbranch_full_integration_test import _remove_project_cleanup_with_retry

    cleanup_steps = []

    class FrozenDeleteService:
        project_url = "https://chatgpt.com/g/g-p-demo/project"

        async def remove_project(self, **_kwargs):
            return project_delete_disabled_result(
                project_url=self.project_url,
                project_name="itest-demo",
                blocked_at_layer="unit_test_service",
            )

    result = asyncio.run(
        _remove_project_cleanup_with_retry(
            cleanup_steps,
            FrozenDeleteService(),
            keep_open=False,
            step_delay_seconds=0.0,
            max_attempts=3,
            project_name="itest-demo",
        )
    )

    assert result["ok"] is True
    assert result["status"] == "project_remove_cleanup_skipped_delete_frozen"
    assert result["postcondition"] == "temporary_project_retained_delete_frozen"
    assert cleanup_steps[-1].ok is True
    assert cleanup_steps[-1].name == "project_remove_cleanup"
