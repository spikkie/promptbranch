from __future__ import annotations

from fastapi.testclient import TestClient

from promptbranch_container_api import app


def test_healthz_reports_service_metadata():
    client = TestClient(app)
    response = client.get("/healthz")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["service"] == "promptbranch-service"
    assert payload["version"] == "0.0.89"


def test_healthz_version_matches_release() -> None:
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["version"] == "0.0.89"


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
        async def list_project_chats(self, *, keep_open: bool = False):
            assert keep_open is False
            return {"ok": True, "count": 1, "chats": [{"id": "abc", "title": "Demo chat"}]}

    monkeypatch.setattr("promptbranch_container_api._service_for", lambda project_url: FakeService())
    client = TestClient(app)
    response = client.get("/v1/chats")
    assert response.status_code == 200
    assert response.json()["count"] == 1


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
        return {'ok': True, 'action': 'test_suite'}

    monkeypatch.setattr('promptbranch_container_api.run_test_suite_async', fake_run_test_suite_async)
    client = TestClient(app)
    response = client.post('/v1/test-suite/run', json={'keep_project': True, 'only': ['project_list_debug']})
    assert response.status_code == 200
    assert response.json()['action'] == 'test_suite'
