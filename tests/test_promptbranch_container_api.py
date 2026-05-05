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
    assert payload["version"] == "0.0.169"


def test_healthz_version_matches_release() -> None:
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["version"] == "0.0.169"


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
