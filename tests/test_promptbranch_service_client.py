from __future__ import annotations

import json
from pathlib import Path

import httpx

from promptbranch_service_client import ChatGPTServiceClient


def test_client_adds_bearer_token_and_healthz_round_trip():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/healthz"
        assert request.headers["Authorization"] == "Bearer secret-token"
        return httpx.Response(200, json={"ok": True, "service": "promptbranch-service"})

    transport = httpx.MockTransport(handler)
    with ChatGPTServiceClient("http://example.test", token="secret-token", transport=transport) as client:
        payload = client.healthz()

    assert payload["ok"] is True
    assert payload["service"] == "promptbranch-service"


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


def test_list_project_sources_passes_project_url_query() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/project-sources"
        assert request.url.params["project_url"] == "https://chatgpt.com/g/demo/project"
        return httpx.Response(200, json={"ok": True, "count": 1, "sources": [{"title": "notes.txt"}]})

    transport = httpx.MockTransport(handler)
    with ChatGPTServiceClient("http://example.test", transport=transport) as client:
        payload = client.list_project_sources(project_url="https://chatgpt.com/g/demo/project")

    assert payload["count"] == 1
    assert payload["sources"][0]["title"] == "notes.txt"



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


def test_list_projects_passes_project_url_query() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/projects"
        assert request.url.params["project_url"] == "https://chatgpt.com/g/demo/project"
        return httpx.Response(200, json={"ok": True, "count": 1, "projects": [{"name": "Demo", "url": "https://chatgpt.com/g/demo/project"}]})

    transport = httpx.MockTransport(handler)
    with ChatGPTServiceClient("http://example.test", transport=transport) as client:
        payload = client.list_projects(project_url="https://chatgpt.com/g/demo/project")

    assert payload["count"] == 1
    assert payload["projects"][0]["name"] == "Demo"


def test_list_project_chats_passes_project_url_query() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chats"
        assert request.url.params["project_url"] == "https://chatgpt.com/g/demo/project"
        assert request.url.params["include_history_fallback"] == "true"
        return httpx.Response(200, json={"ok": True, "count": 1, "chats": [{"id": "abc", "title": "Demo chat"}]})

    transport = httpx.MockTransport(handler)
    with ChatGPTServiceClient("http://example.test", transport=transport) as client:
        payload = client.list_project_chats(project_url="https://chatgpt.com/g/demo/project")

    assert payload["count"] == 1
    assert payload["chats"][0]["title"] == "Demo chat"


def test_get_chat_posts_expected_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chats/get"
        payload = json.loads(request.read().decode("utf-8"))
        assert payload == {
            "conversation_url": "https://chatgpt.com/g/demo/c/123",
            "keep_open": False,
            "project_url": "https://chatgpt.com/g/demo/project",
        }
        return httpx.Response(200, json={"ok": True, "conversation_id": "123", "title": "Demo chat", "turn_count": 2, "turns": []})

    transport = httpx.MockTransport(handler)
    with ChatGPTServiceClient("http://example.test", transport=transport) as client:
        payload = client.get_chat("https://chatgpt.com/g/demo/c/123", project_url="https://chatgpt.com/g/demo/project")

    assert payload["conversation_id"] == "123"


def test_run_test_suite_posts_expected_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/test-suite/run"
        payload = json.loads(request.read().decode("utf-8"))
        assert payload == {"keep_project": True, "only": ["project_list_debug"]}
        return httpx.Response(200, json={"ok": True, "steps": []})

    transport = httpx.MockTransport(handler)
    with ChatGPTServiceClient("http://example.test", transport=transport) as client:
        payload = client.run_test_suite({"keep_project": True, "only": ["project_list_debug"]})

    assert payload["ok"] is True


def test_add_project_source_file_defaults_name_to_file_basename(tmp_path: Path) -> None:
    file_path = tmp_path / "architecture-process_0.1.16.zip"
    file_path.write_bytes(b"zip-bytes")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/project-sources"
        content_type = request.headers["Content-Type"]
        assert content_type.startswith("multipart/form-data; boundary=")
        body = request.read().decode("utf-8", errors="ignore")
        assert 'name="name"' in body
        assert "architecture-process_0.1.16.zip" in body
        assert 'name="overwrite_existing"' in body
        assert "true" in body
        return httpx.Response(200, json={"ok": True, "action": "add"})

    transport = httpx.MockTransport(handler)
    with ChatGPTServiceClient("http://example.test", transport=transport) as client:
        payload = client.add_project_source(source_kind="file", file_path=str(file_path))

    assert payload["action"] == "add"


def test_add_project_source_file_normalizes_display_name_to_basename(tmp_path: Path) -> None:
    file_path = tmp_path / "candlecast-src-0.19.5.82.2.zip"
    file_path.write_bytes(b"zip")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/project-sources"
        body = request.read().decode("utf-8", errors="ignore")
        assert "candlecast-src-0.19.5.82.2.zip" in body
        assert "/tmp/releases/candlecast-src-0.19.5.82.2.zip" not in body
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    with ChatGPTServiceClient("http://example.test", transport=transport) as client:
        payload = client.add_project_source(
            source_kind="file",
            file_path=str(file_path),
            display_name="/tmp/releases/candlecast-src-0.19.5.82.2.zip",
        )

    assert payload["ok"] is True
