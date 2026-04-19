from __future__ import annotations

import json
from pathlib import Path

import httpx

from chatgpt_service_client import ChatGPTServiceClient


def test_client_adds_bearer_token_and_healthz_round_trip():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/healthz"
        assert request.headers["Authorization"] == "Bearer secret-token"
        return httpx.Response(200, json={"ok": True, "service": "chatgpt-docker-service"})

    transport = httpx.MockTransport(handler)
    with ChatGPTServiceClient("http://example.test", token="secret-token", transport=transport) as client:
        payload = client.healthz()

    assert payload["ok"] is True
    assert payload["service"] == "chatgpt-docker-service"


def test_ask_with_file_posts_multipart_and_returns_answer(tmp_path: Path):
    file_path = tmp_path / "note.txt"
    file_path.write_text("hello", encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/ask"
        content_type = request.headers["Content-Type"]
        assert content_type.startswith("multipart/form-data; boundary=")
        body = request.read().decode("utf-8", errors="ignore")
        assert "Reply with one short sentence." in body
        assert "note.txt" in body
        return httpx.Response(200, json={"ok": True, "answer": "ready", "conversation_url": "https://chatgpt.com/g/demo/c/123"})

    transport = httpx.MockTransport(handler)
    with ChatGPTServiceClient("http://example.test", transport=transport) as client:
        answer = client.ask("Reply with one short sentence.", file_path=str(file_path))

    assert answer == "ready"


def test_ask_result_returns_full_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/ask"
        return httpx.Response(
            200,
            json={
                "ok": True,
                "answer": "ready",
                "conversation_url": "https://chatgpt.com/g/demo/c/123",
            },
        )

    transport = httpx.MockTransport(handler)
    with ChatGPTServiceClient("http://example.test", transport=transport) as client:
        payload = client.ask_result("Reply with one short sentence.")

    assert payload["answer"] == "ready"
    assert payload["conversation_url"] == "https://chatgpt.com/g/demo/c/123"


def test_remove_project_source_posts_expected_json():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/project-sources/remove"
        payload = json.loads(request.read().decode("utf-8"))
        assert payload == {
            "source_name": "Notes",
            "exact": True,
            "keep_open": False,
        }
        return httpx.Response(200, json={"ok": True, "removed": True})

    transport = httpx.MockTransport(handler)
    with ChatGPTServiceClient("http://example.test", transport=transport) as client:
        payload = client.remove_project_source("Notes", exact=True)

    assert payload["removed"] is True


def test_resolve_project_posts_expected_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/projects/resolve"
        payload = json.loads(request.read().decode("utf-8"))
        assert payload == {
            "name": "Demo",
            "keep_open": False,
            "project_url": "https://chatgpt.com/g/demo/project",
        }
        return httpx.Response(200, json={"ok": True, "match_count": 1})

    transport = httpx.MockTransport(handler)
    with ChatGPTServiceClient("http://example.test", transport=transport) as client:
        payload = client.resolve_project("Demo", project_url="https://chatgpt.com/g/demo/project")

    assert payload["match_count"] == 1


def test_project_source_capabilities_passes_project_url_query() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/project-source-capabilities"
        assert request.url.params["project_url"] == "https://chatgpt.com/g/demo/project"
        return httpx.Response(200, json={"ok": True, "available_source_kinds": ["file", "text"]})

    transport = httpx.MockTransport(handler)
    with ChatGPTServiceClient("http://example.test", transport=transport) as client:
        payload = client.discover_project_source_capabilities(project_url="https://chatgpt.com/g/demo/project")

    assert payload["available_source_kinds"] == ["file", "text"]



def test_http_error_includes_detail_from_json_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "RuntimeError: chrome profile in use"})

    transport = httpx.MockTransport(handler)
    with ChatGPTServiceClient("http://example.test", transport=transport) as client:
        try:
            client.login_check()
        except httpx.HTTPStatusError as exc:
            assert "chrome profile in use" in str(exc)
        else:  # pragma: no cover - defensive
            raise AssertionError("expected HTTPStatusError")


def test_create_project_posts_expected_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/projects/create"
        payload = json.loads(request.read().decode("utf-8"))
        assert payload == {
            "name": "Demo",
            "icon": "folder",
            "color": "blue",
            "memory_mode": "project-only",
            "keep_open": False,
            "project_url": "https://chatgpt.com/g/demo/project",
        }
        return httpx.Response(200, json={"ok": True, "project_url": "https://chatgpt.com/g/new/project"})

    transport = httpx.MockTransport(handler)
    with ChatGPTServiceClient("http://example.test", transport=transport) as client:
        payload = client.create_project(
            "Demo",
            icon="folder",
            color="blue",
            memory_mode="project-only",
            project_url="https://chatgpt.com/g/demo/project",
        )

    assert payload["project_url"] == "https://chatgpt.com/g/new/project"


def test_ask_result_includes_conversation_url_form_field() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/ask"
        body = request.read().decode("utf-8", errors="ignore")
        assert "conversation_url" in body
        assert "conversation_url=https%3A%2F%2Fchatgpt.com%2Fg%2Fdemo%2Fc%2F123" in body
        return httpx.Response(200, json={"ok": True, "answer": "ready", "conversation_url": "https://chatgpt.com/g/demo/c/123"})

    transport = httpx.MockTransport(handler)
    with ChatGPTServiceClient("http://example.test", transport=transport) as client:
        payload = client.ask_result("Reply with one short sentence.", conversation_url="https://chatgpt.com/g/demo/c/123")

    assert payload["conversation_url"] == "https://chatgpt.com/g/demo/c/123"
