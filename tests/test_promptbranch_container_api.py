from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from promptbranch_container_api import app


def test_healthz_reports_service_metadata():
    client = TestClient(app)
    response = client.get("/healthz")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["service"] == "promptbranch-service"
    assert payload["version"] == "0.1.23"


def test_healthz_version_matches_release() -> None:
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["version"] == "0.1.23"


def test_list_projects_endpoint_uses_service(monkeypatch) -> None:
    class FakeService:
        async def list_projects(self, *, keep_open: bool = False):
            assert keep_open is False
            return {"ok": True, "count": 1, "projects": [{"name": "Demo", "url": "https://chatgpt.com/g/demo/project"}]}

    monkeypatch.setattr("promptbranch_container_api._service_for", lambda project_url: FakeService())
    client = TestClient(app)
    response = client.get("/v1/projects")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["projects"][0]["name"] == "Demo"


def test_list_project_chats_endpoint_uses_service(monkeypatch) -> None:
    class FakeService:
        async def list_project_chats(self, *, keep_open: bool = False, include_history_fallback: bool = True):
            assert keep_open is False
            assert include_history_fallback is True
            return {"ok": True, "count": 1, "chats": [{"id": "abc", "title": "Demo chat"}]}

    monkeypatch.setattr("promptbranch_container_api._service_for", lambda project_url: FakeService())
    client = TestClient(app)
    response = client.get("/v1/chats")
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_list_project_sources_endpoint_uses_service(monkeypatch) -> None:
    class FakeService:
        async def list_project_sources(self, *, keep_open: bool = False):
            assert keep_open is False
            return {"ok": True, "count": 1, "sources": [{"title": "architecture-process_0.1.16.zip"}]}

    monkeypatch.setattr("promptbranch_container_api._service_for", lambda project_url: FakeService())
    client = TestClient(app)
    response = client.get("/v1/project-sources")
    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["sources"][0]["title"] == "architecture-process_0.1.16.zip"


def test_get_chat_endpoint_uses_service(monkeypatch) -> None:
    class FakeService:
        async def get_chat(self, *, conversation_url: str, keep_open: bool = False):
            assert conversation_url == "https://chatgpt.com/g/demo/c/123"
            assert keep_open is False
            return {"ok": True, "conversation_id": "123", "title": "Demo chat", "turn_count": 1, "turns": []}

    monkeypatch.setattr("promptbranch_container_api._service_for", lambda project_url: FakeService())
    client = TestClient(app)
    response = client.post("/v1/chats/get", json={"conversation_url": "https://chatgpt.com/g/demo/c/123"})
    assert response.status_code == 200
    assert response.json()["conversation_id"] == "123"


def test_test_suite_frontend_serves_html():
    client = TestClient(app)
    response = client.get('/ui/test-suite')
    assert response.status_code == 200
    assert 'promptbranch test suite' in response.text


def test_run_test_suite_endpoint_uses_helper(monkeypatch) -> None:
    async def fake_run_test_suite_async(**kwargs):
        assert kwargs['keep_project'] is True
        assert kwargs['only'] == ['project_list_debug']
        assert kwargs.get('profile') == 'browser'
        return {'ok': True, 'action': 'test_suite'}

    monkeypatch.setattr('promptbranch_container_api.run_test_suite_async', fake_run_test_suite_async)
    client = TestClient(app)
    response = client.post('/v1/test-suite/run', json={'keep_project': True, 'only': ['project_list_debug'], 'profile': 'browser'})
    assert response.status_code == 200
    assert response.json()['action'] == 'test_suite'


def test_add_project_source_file_preserves_uploaded_basename_and_defaults_display_name(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeService:
        async def add_project_source(self, *, source_kind: str, value=None, file_path=None, display_name=None, keep_open: bool = False, overwrite_existing: bool = True):
            captured["source_kind"] = source_kind
            captured["overwrite_existing"] = overwrite_existing
            captured["file_path"] = file_path
            captured["display_name"] = display_name
            captured["keep_open"] = keep_open
            assert file_path is not None
            path = Path(file_path)
            captured["basename"] = path.name
            captured["exists_during_call"] = path.exists()
            return {"ok": True, "file_path": file_path, "display_name": display_name}

    monkeypatch.setattr("promptbranch_container_api._service_for", lambda project_url: FakeService())
    client = TestClient(app)
    response = client.post(
        "/v1/project-sources",
        data={"type": "file"},
        files={"file": ("architecture-process_0.1.16.zip", b"zip-bytes", "application/zip")},
    )

    assert response.status_code == 200
    assert response.json()["display_name"] == "architecture-process_0.1.16.zip"
    assert captured["source_kind"] == "file"
    assert captured["basename"] == "architecture-process_0.1.16.zip"
    assert captured["display_name"] == "architecture-process_0.1.16.zip"
    assert captured["exists_during_call"] is True
    assert captured["overwrite_existing"] is True


def test_ask_file_upload_preserves_uploaded_basename(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeService:
        async def ask_question_result(self, *, prompt: str, file_path=None, conversation_url=None, expect_json: bool, keep_open: bool = False, retries=None):
            captured["prompt"] = prompt
            captured["file_path"] = file_path
            assert file_path is not None
            path = Path(file_path)
            captured["basename"] = path.name
            captured["exists_during_call"] = path.exists()
            return {"answer": "ready", "conversation_url": None}

    monkeypatch.setattr("promptbranch_container_api._service_for", lambda project_url: FakeService())
    client = TestClient(app)
    response = client.post(
        "/v1/ask",
        data={"prompt": "hello"},
        files={"file": ("architecture-process_0.1.16.zip", b"zip-bytes", "application/zip")},
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "ready"
    assert captured["basename"] == "architecture-process_0.1.16.zip"
    assert captured["exists_during_call"] is True


def test_ask_multiple_attachments_preserve_uploaded_basenames(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeService:
        async def ask_question_result(self, **kwargs):
            paths = [Path(path) for path in kwargs["attachment_paths"]]
            captured["basenames"] = [path.name for path in paths]
            captured["exists_during_call"] = [path.exists() for path in paths]
            captured["file_path"] = kwargs.get("file_path")
            return {"answer": "ready", "conversation_url": None}

    monkeypatch.setattr("promptbranch_container_api._service_for", lambda project_url: FakeService())
    client = TestClient(app)
    response = client.post(
        "/v1/ask",
        data={"prompt": "hello"},
        files=[
            ("attachments", ("one.log", b"one", "text/plain")),
            ("attachments", ("two.log", b"two", "text/plain")),
        ],
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "ready"
    assert captured["basenames"] == ["one.log", "two.log"]
    assert captured["exists_during_call"] == [True, True]
    assert captured["file_path"] is None


def test_ask_endpoint_preserves_partial_timeout_result(monkeypatch) -> None:
    class FakeService:
        async def ask_question_result(self, **kwargs):
            return {
                "ok": False,
                "status": "assistant_response_timeout",
                "error": "timed out",
                "error_type": "ResponseTimeoutError",
                "timeout_layer": "assistant_response",
                "answer": None,
                "conversation_url": "https://chatgpt.com/c/abc",
                "submit_evidence": {"clicked": True},
                "partial_result": True,
                "response_timeout_ms": 600000,
                "debug_artifacts": ["debug_artifacts/response_wait.txt"],
            }

    monkeypatch.setattr("promptbranch_container_api._service_for", lambda project_url: FakeService())
    client = TestClient(app)
    response = client.post("/v1/ask", data={"prompt": "hello"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert payload["status"] == "assistant_response_timeout"
    assert payload["timeout_layer"] == "assistant_response"
    assert payload["submit_evidence"] == {"clicked": True}
    assert payload["partial_result"] is True
    assert payload["debug_artifacts"] == ["debug_artifacts/response_wait.txt"]

def test_ask_endpoint_internal_deadline_preserves_latest_submit_progress(monkeypatch) -> None:
    class FakeService:
        async def ask_question_result(self, **kwargs):
            import asyncio
            await asyncio.sleep(2.0)
            return {"answer": "late"}

    preserved_submit = {
        "submit_confirmed": True,
        "submit_confirmed_by": ["backend_task_message"],
        "submit_backend_task_message_found": True,
        "post_submit_user_turn_visible": False,
        "submit_backend_confirmed_but_user_turn_not_visible": True,
    }
    preserved_timings = {
        "submit_confirmed": True,
        "submit_visibility_classification": "backend_confirmed_but_user_turn_not_visible",
    }

    monkeypatch.setattr("promptbranch_container_api._service_for", lambda project_url: FakeService())
    monkeypatch.setattr(
        "promptbranch_container_api.get_latest_ask_progress",
        lambda: {
            "status": "submit_confirmed",
            "conversation_url": "https://chatgpt.com/g/demo/c/chat-1",
            "submit_evidence": preserved_submit,
            "ask_phase_timings": preserved_timings,
            "updated_at_monotonic": 123.0,
        },
    )

    client = TestClient(app)
    response = client.post("/v1/ask", data={"prompt": "hello", "service_timeout_seconds": "1"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert payload["status"] == "submit_confirmed_backend_only_ui_not_hydrated"
    assert payload["timeout_layer"] == "submit_visibility"
    assert payload["conversation_url"] == "https://chatgpt.com/g/demo/c/chat-1"
    assert payload["submit_evidence"] == preserved_submit
    assert payload["ask_phase_timings"] == preserved_timings
    assert payload["progress_status"] == "submit_confirmed"


def test_container_service_does_not_clear_singleton_locks_by_default(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS", raising=False)
    monkeypatch.setenv("PROMPTBRANCH_PROFILE_DIR", str(tmp_path / ".pb_profile"))

    from promptbranch_container_api import _build_service

    svc = _build_service(project_url_override="https://chatgpt.com/g/g-p-demo/project")

    assert svc.settings.clear_singleton_locks is False


def test_browser_status_endpoint_reports_service_status(monkeypatch) -> None:
    class FakeService:
        def browser_status(self):
            return {"ok": True, "status": "available", "queue_enabled": False}

    monkeypatch.setattr("promptbranch_container_api._service_for", lambda project_url: FakeService())
    client = TestClient(app)
    response = client.get("/v1/browser/status")

    assert response.status_code == 200
    assert response.json()["status"] == "available"
    assert response.json()["queue_enabled"] is False


def test_ask_endpoint_exposes_phase_timings(monkeypatch) -> None:
    class FakeService:
        async def ask_question_result(self, **kwargs):
            return {
                "answer": "done",
                "conversation_url": "https://chatgpt.com/g/demo/c/1",
                "submit_evidence": {"submit_method": "enter_fallback"},
                "ask_phase_timings": {
                    "total_seconds": 6.0,
                    "submit_method": "enter_fallback",
                    "submit_wait_seconds": 5.0,
                    "lock_wait_seconds": 0.0,
                },
            }

    monkeypatch.setattr("promptbranch_container_api._service_for", lambda project_url: FakeService())
    client = TestClient(app)
    response = client.post("/v1/ask", data={"prompt": "hello"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["ask_phase_timings"]["total_seconds"] == 6.0
    assert payload["ask_phase_timings"]["submit_method"] == "enter_fallback"


def test_add_project_source_passes_profile_lock_wait_seconds(monkeypatch, tmp_path) -> None:
    captured: dict[str, object] = {}

    class FakeService:
        async def add_project_source(self, **kwargs):
            captured.update(kwargs)
            return {"ok": True}

    file_path = tmp_path / "demo.zip"
    file_path.write_bytes(b"zip")
    monkeypatch.setattr("promptbranch_container_api._service_for", lambda project_url: FakeService())
    client = TestClient(app)
    with file_path.open("rb") as handle:
        response = client.post(
            "/v1/project-sources",
            data={"type": "file", "profile_lock_wait_seconds": "120"},
            files={"file": (file_path.name, handle, "application/octet-stream")},
        )

    assert response.status_code == 200
    assert captured["profile_lock_wait_seconds"] == 120.0


def test_browser_context_unavailable_payload_is_returned_from_service_ask(tmp_path, monkeypatch):
    import asyncio

    from promptbranch_automation.service import ChatGPTAutomationService, ChatGPTAutomationSettings
    from promptbranch_browser_auth.exceptions import BrowserContextUnavailableError

    settings = ChatGPTAutomationSettings(
        project_url="https://chatgpt.com/g/demo/project",
        email=None,
        password=None,
        profile_dir=str(tmp_path / "profile"),
        headless=False,
        use_patchright=True,
        max_retries=0,
    )
    service = ChatGPTAutomationService(settings)

    class FailingBot:
        async def ask_question_result(self, **kwargs):
            raise BrowserContextUnavailableError(
                "browser_launch_failed: RuntimeError: Protocol error (Network.setCacheDisabled)",
                payload={
                    "ok": False,
                    "status": "browser_launch_failed",
                    "error": "Protocol error (Network.setCacheDisabled)",
                    "error_type": "RuntimeError",
                    "browser_driver": "patchright",
                    "browser_mode": "local_headed_patchright",
                    "headless": False,
                },
            )

    monkeypatch.setattr(service, "_build_bot", lambda: FailingBot())

    payload = asyncio.run(service.ask_question_result(prompt="print echo 1", retries=0))

    assert payload["ok"] is False
    assert payload["status"] == "browser_launch_failed"
    assert payload["answer"] is None
    assert payload["browser_driver"] == "patchright"
    assert payload["ask_phase_timings"]["submit_method"] is None
