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
    assert payload["version"] == "0.0.79"


def test_healthz_version_matches_release() -> None:
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["version"] == "0.0.79"


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
