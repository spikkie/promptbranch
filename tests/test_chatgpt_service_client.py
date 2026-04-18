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
        return httpx.Response(200, json={"ok": True, "answer": "ready"})

    transport = httpx.MockTransport(handler)
    with ChatGPTServiceClient("http://example.test", transport=transport) as client:
        answer = client.ask("Reply with one short sentence.", file_path=str(file_path))

    assert answer == "ready"


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
