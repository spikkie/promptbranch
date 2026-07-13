from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from promptbranch_browser_auth.client import ChatGPTBrowserClient
from promptbranch_browser_auth.config import ChatGPTBrowserConfig
from promptbranch_container_api import app


def browser_client(tmp_path: Path) -> ChatGPTBrowserClient:
    return ChatGPTBrowserClient(
        ChatGPTBrowserConfig(
            project_url="https://chatgpt.com/",
            profile_dir=str(tmp_path / "profile"),
            debug=False,
        )
    )


def test_protocol_mapping_uses_semantic_ids_and_never_empty_key(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    mapping = client._protocol_replacement_mapping(
        source_processed_file_id="file_00000000111122223333444455556666",
        source_library_metadata_object_id="libfile_source",
        source_filename="visible.txt",
        target_processed_file_id="file_aaaaaaaa111122223333444455556666",
        target_library_metadata_object_id="libfile_target",
        target_filename="target.txt",
    )
    assert "" not in mapping
    assert mapping["libfile_source"] == "libfile_target"
    assert mapping["visible.txt"] == "target.txt"
    assert mapping["00000000-1111-2222-3333-444455556666"] == "aaaaaaaa-1111-2222-3333-444455556666"


def test_inventory_discovery_ignores_upload_stream_and_selects_inventory(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    watch = {
        "events": [
            {
                "kind": "response",
                "phase": "visible_library_file_upload",
                "method": "POST",
                "_raw_url": "https://chatgpt.com/backend-api/files/process_upload_stream",
                "_raw_body": '{"metadata_object_id":"libfile_visible","library_file_name":"visible.txt"}',
                "extracted_records": [{"file_id": "libfile_visible", "filename": "visible.txt"}],
            },
            {
                "kind": "response",
                "phase": "visible_library_active_inventory",
                "method": "GET",
                "url": "https://chatgpt.com/backend-api/library/items?<redacted>",
                "_raw_url": "https://chatgpt.com/backend-api/library/items?search=visible.txt",
                "_raw_post_data": None,
                "_raw_headers": {"accept": "application/json"},
                "status": 200,
                "extracted_records": [{"file_id": "libfile_visible", "filename": "visible.txt"}],
            },
        ]
    }
    protocol = client._discover_backend_inventory_protocol(
        watch,
        id_candidates=["libfile_visible"],
        filename="visible.txt",
        phases={"visible_library_file_upload", "visible_library_active_inventory"},
    )
    assert protocol is not None
    assert protocol["method"] == "GET"
    assert "library/items" in protocol["_raw_url"]


def test_delete_protocol_requires_exact_id_in_mutation(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    watch = {
        "events": [
            {
                "kind": "response",
                "phase": "visible_library_soft_delete",
                "method": "POST",
                "_raw_url": "https://chatgpt.com/backend-api/library/delete",
                "_raw_post_data": '{"id":"libfile_visible"}',
                "_raw_body": "{}",
                "status": 200,
                "request_headers": {"content-type": "application/json"},
            },
            {
                "kind": "response",
                "phase": "visible_library_soft_delete",
                "method": "POST",
                "_raw_url": "https://chatgpt.com/backend-api/telemetry",
                "_raw_post_data": '{"filename":"visible.txt"}',
                "_raw_body": "{}",
                "status": 200,
            },
        ]
    }
    protocol = client._discover_backend_delete_protocol(
        watch,
        id_candidates=["libfile_visible"],
        filename="visible.txt",
        phase="visible_library_soft_delete",
    )
    assert protocol is not None
    assert protocol["_raw_post_data"] == '{"id":"libfile_visible"}'


def test_public_trace_removes_raw_protocol_material(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    trace = client._public_fetch_xhr_protocol_trace(
        {
            "installed": True,
            "events": [
                {
                    "kind": "request",
                    "phase": "project_source_upload",
                    "url": "https://chatgpt.com/backend-api/files?<redacted>",
                    "_raw_url": "https://chatgpt.com/backend-api/files?secret=value",
                    "_raw_post_data": "secret",
                }
            ],
        }
    )
    assert trace["capture_scope"] == "all_fetch_xhr"
    assert trace["event_count"] == 1
    assert all(not key.startswith("_") for key in trace["events"][0])


def test_endpoint_returns_browser_diagnostic_and_preserves_safety(monkeypatch) -> None:
    class FakeService:
        async def run_library_backend_protocol_reupload_diagnostic(self, **kwargs):
            assert kwargs["project_name_prefix"] == "itest-custom"
            return {
                "ok": True,
                "status": "diagnostic_completed",
                "conclusion": "backend_delete_protocol_not_discovered",
                "fetch_xhr_trace": {"capture_scope": "all_fetch_xhr", "event_count": 4},
            }

    async def fake_preflight(_project_url, *, allow_project_source_mutation: bool):
        assert allow_project_source_mutation is True
        return {"auth_readiness": {"ok": True}, "runtime": {"ok": True}}

    monkeypatch.setattr("promptbranch_container_api._service_for", lambda _url: FakeService())
    monkeypatch.setattr("promptbranch_container_api._require_project_source_mutation_preflight", fake_preflight)
    response = TestClient(app).post(
        "/v1/diagnostics/library-backend-protocol-reupload",
        json={
            "project_name_prefix": "itest-custom",
            "allow_project_source_mutation": True,
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["conclusion"] == "backend_delete_protocol_not_discovered"
    assert payload["fetch_xhr_trace"]["capture_scope"] == "all_fetch_xhr"
    assert payload["safety"]["existing_suffix_evidence_project_touched"] is False
    assert payload["project_source_mutation_gate"] == "docker_browser_parity_preflight_passed"


def test_public_browser_method_forces_history_shield_and_restores_mode(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    client.config.conversation_history_request_shield_mode = "disabled"
    observed = {}

    async def fake_run_with_context(**kwargs):
        observed["mode"] = client.config.conversation_history_request_shield_mode
        observed["operation_name"] = kwargs["operation_name"]
        return {"ok": True, "status": "diagnostic_completed", "conclusion": "diagnostic_inconclusive"}

    client._run_with_context = fake_run_with_context  # type: ignore[method-assign]
    result = asyncio.run(client.run_library_backend_protocol_reupload_diagnostic())
    assert result["status"] == "diagnostic_completed"
    assert observed["mode"] == "fulfill_empty"
    assert observed["operation_name"] == "library_backend_protocol_reupload_diagnostic"
    assert client.config.conversation_history_request_shield_mode == "disabled"
