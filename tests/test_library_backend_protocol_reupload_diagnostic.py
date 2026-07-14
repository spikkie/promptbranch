from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from promptbranch_browser_auth.client import ChatGPTBrowserClient
from promptbranch_browser_auth.config import ChatGPTBrowserConfig
from promptbranch_browser_auth.exceptions import ResponseTimeoutError
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


def test_public_trace_reports_bounded_task_settlement(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    settlement = {
        "ok": False,
        "status": "fetch_xhr_protocol_watch_settle_timeout",
        "task_count": 3,
        "completed_task_count": 2,
        "cancelled_task_count": 1,
        "failed_task_count": 0,
        "pending_task_count": 1,
        "detached_task_count": 0,
        "unresolved_tasks": [
            {
                "task_kind": "response_capture",
                "phase": "visible_library_file_upload",
                "method": "GET",
                "resource_type": "fetch",
                "url": "https://chatgpt.com/backend-api/files/library/nodes?q=<redacted>",
                "content_type": "application/json",
            }
        ],
    }
    trace = client._public_fetch_xhr_protocol_trace(
        {
            "installed": True,
            "events": [],
            "last_settlement": settlement,
            "settlement_history": [settlement],
            "disposed_pending_task_count": 0,
        }
    )
    assert trace["task_settlement"] == settlement
    assert trace["task_settlement_history"] == [settlement]
    assert trace["task_settlement"]["pending_task_count"] == 1
    assert trace["task_settlement"]["unresolved_tasks"][0]["phase"] == "visible_library_file_upload"


def test_fetch_xhr_protocol_watch_settlement_is_bounded_and_classifies_pending_task(tmp_path: Path) -> None:
    client = browser_client(tmp_path)

    async def scenario() -> tuple[dict, asyncio.Task]:
        blocker = asyncio.Event()
        task = asyncio.create_task(blocker.wait())
        watch = {
            "tasks": [task],
            "task_metadata": {
                id(task): {
                    "task_kind": "response_capture",
                    "phase": "visible_library_file_upload",
                    "method": "GET",
                    "resource_type": "fetch",
                    "url": "https://chatgpt.com/backend-api/files/library/nodes?q=<redacted>",
                    "content_type": "application/json",
                }
            },
            "settlement_history": [],
        }
        result = await client._settle_fetch_xhr_protocol_watch(
            watch,
            timeout_seconds=0.01,
            cancel_timeout_seconds=0.05,
            raise_on_timeout=False,
        )
        return result, task

    result, task = asyncio.run(scenario())
    assert result["ok"] is False
    assert result["status"] == "fetch_xhr_protocol_watch_settle_timeout"
    assert result["pending_task_count"] == 1
    assert result["cancelled_task_count"] == 1
    assert result["detached_task_count"] == 0
    assert result["unresolved_tasks"] == [
        {
            "task_kind": "response_capture",
            "phase": "visible_library_file_upload",
            "method": "GET",
            "resource_type": "fetch",
            "url": "https://chatgpt.com/backend-api/files/library/nodes?q=<redacted>",
            "content_type": "application/json",
        }
    ]
    assert task.cancelled()


def test_fetch_xhr_protocol_watch_settlement_raises_explicit_timeout(tmp_path: Path) -> None:
    client = browser_client(tmp_path)

    async def scenario() -> None:
        blocker = asyncio.Event()
        task = asyncio.create_task(blocker.wait())
        watch = {
            "tasks": [task],
            "task_metadata": {id(task): {"task_kind": "response_capture", "phase": "test"}},
            "settlement_history": [],
        }
        with pytest.raises(ResponseTimeoutError, match="fetch_xhr_protocol_watch_settle_timeout"):
            await client._settle_fetch_xhr_protocol_watch(
                watch,
                timeout_seconds=0.01,
                cancel_timeout_seconds=0.05,
            )

    asyncio.run(scenario())


def test_fetch_xhr_protocol_watch_never_reads_event_stream_body(tmp_path: Path) -> None:
    client = browser_client(tmp_path)

    class Context:
        def __init__(self) -> None:
            self.handlers = {}

        def on(self, name, handler) -> None:
            self.handlers[name] = handler

        def remove_listener(self, name, handler) -> None:
            assert self.handlers.get(name) is handler

    class Request:
        resource_type = "fetch"
        method = "POST"
        url = "https://chatgpt.com/backend-api/files/process_upload_stream"
        headers = {"accept": "text/event-stream"}
        post_data = "{}"

    class Response:
        status = 200
        url = Request.url

        def __init__(self, request) -> None:
            self.request = request
            self.text_called = False

        async def all_headers(self):
            return {"content-type": "text/event-stream"}

        async def text(self):
            self.text_called = True
            raise AssertionError("streaming response body must not be awaited")

    async def scenario() -> tuple[dict, Response]:
        context = Context()
        watch = client._install_fetch_xhr_protocol_watch(context)
        request = Request()
        response = Response(request)
        context.handlers["request"](request)
        context.handlers["response"](response)
        settlement = await client._settle_fetch_xhr_protocol_watch(watch)
        assert settlement["ok"] is True
        return watch, response

    watch, response = asyncio.run(scenario())
    assert response.text_called is False
    response_events = [event for event in watch["events"] if event.get("kind") == "response"]
    assert len(response_events) == 1
    assert response_events[0]["content_type"] == "text/event-stream"
    assert response_events[0]["body_error"] == "streaming_response_body_omitted"


def test_fetch_xhr_protocol_watch_bounds_non_streaming_response_text(tmp_path: Path) -> None:
    client = browser_client(tmp_path)

    class Context:
        def __init__(self) -> None:
            self.handlers = {}

        def on(self, name, handler) -> None:
            self.handlers[name] = handler

    class Request:
        resource_type = "fetch"
        method = "GET"
        url = "https://chatgpt.com/backend-api/files/library/nodes?q=test"
        headers = {"accept": "application/json"}
        post_data = None

    class Response:
        status = 200
        url = Request.url

        def __init__(self, request) -> None:
            self.request = request

        async def all_headers(self):
            return {"content-type": "application/json"}

        async def text(self):
            await asyncio.Event().wait()

    async def scenario() -> dict:
        context = Context()
        watch = client._install_fetch_xhr_protocol_watch(context)
        watch["response_body_timeout_seconds"] = 0.01
        request = Request()
        context.handlers["request"](request)
        context.handlers["response"](Response(request))
        settlement = await client._settle_fetch_xhr_protocol_watch(
            watch,
            timeout_seconds=0.25,
        )
        assert settlement["ok"] is True
        return watch

    watch = asyncio.run(scenario())
    response_events = [event for event in watch["events"] if event.get("kind") == "response"]
    assert len(response_events) == 1
    assert response_events[0]["body_error"] == "response_body_timeout"
    assert response_events[0]["body_sample"] == ""


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


def test_library_nodes_record_preserves_processed_and_libfile_identities(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    records = client._extract_library_file_records_from_payload(
        {
            "items": [
                {
                    "kind": "file",
                    "id": "libfile_1234567890abcdef1234567890abcdef",
                    "file_id": "file_00000000111122223333444455556666",
                    "name": "visible.txt",
                    "gizmo_id": "g-p-test-project",
                    "trashed_at": None,
                }
            ]
        },
        source_url="https://chatgpt.com/backend-api/files/library/nodes",
    )
    assert len(records) == 1
    record = records[0]
    assert record["processed_file_id"] == "file_00000000111122223333444455556666"
    assert record["library_metadata_object_id"] == "libfile_1234567890abcdef1234567890abcdef"
    assert record["identity_candidates"] == [
        "libfile_1234567890abcdef1234567890abcdef",
        "file_00000000111122223333444455556666",
    ]
    assert client._protocol_exact_record_present(
        records,
        ["libfile_1234567890abcdef1234567890abcdef"],
    )


def test_inventory_discovery_accepts_empty_library_nodes_search_response(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    watch = {
        "events": [
            {
                "kind": "response",
                "phase": "visible_library_file_upload",
                "method": "GET",
                "url": "https://chatgpt.com/backend-api/files/library/nodes?q=<redacted>",
                "_raw_url": "https://chatgpt.com/backend-api/files/library/nodes?q=visible.txt",
                "_raw_post_data": None,
                "_raw_headers": {"accept": "application/json"},
                "status": 200,
                "extracted_records": [],
            }
        ]
    }
    protocol = client._discover_backend_inventory_protocol(
        watch,
        id_candidates=["libfile_1234567890abcdef1234567890abcdef"],
        filename="visible.txt",
        phases={"visible_library_file_upload"},
    )
    assert protocol is not None
    assert protocol["method"] == "GET"
    assert protocol["endpoint_discovered_from_empty_inventory"] is True
    assert "/backend-api/files/library/nodes" in protocol["_raw_url"]


def test_exact_backend_inventory_poll_uses_libfile_identity(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    libfile_id = "libfile_1234567890abcdef1234567890abcdef"
    responses = iter(
        [
            {"ok": True, "records": []},
            {
                "ok": True,
                "records": [
                    {
                        "file_id": "file_00000000111122223333444455556666",
                        "library_metadata_object_id": libfile_id,
                        "identity_candidates": [libfile_id, "file_00000000111122223333444455556666"],
                    }
                ],
            },
            {
                "ok": True,
                "records": [
                    {
                        "file_id": "file_00000000111122223333444455556666",
                        "library_metadata_object_id": libfile_id,
                        "identity_candidates": [libfile_id, "file_00000000111122223333444455556666"],
                    }
                ],
            },
        ]
    )

    async def fake_replay(*_args, **_kwargs):
        return next(responses)

    class FakePage:
        async def wait_for_timeout(self, _milliseconds: int) -> None:
            return None

    client._replay_backend_protocol = fake_replay  # type: ignore[method-assign]
    result = asyncio.run(
        client._poll_exact_backend_inventory_presence(
            FakePage(),
            protocol={"method": "GET", "_raw_url": "https://chatgpt.com/backend-api/files/library/nodes?q=visible.txt"},
            id_candidates=[libfile_id],
            required_stable_observations=2,
            max_attempts=3,
            poll_ms=1,
        )
    )
    assert result["ok"] is True
    assert result["status"] == "exact_library_identity_stably_present"
    assert len(result["observations"]) == 3


def test_protocol_trace_is_complete_and_body_samples_are_safely_scoped(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    events = [
        {
            "kind": "response",
            "phase": "noise",
            "url": "https://chatgpt.com/backend-api/sentinel/chat-requirements/finalize",
            "body_sample": '{"token":"secret","email":"person@example.com"}',
            "request_headers": {
                "chatgpt-account-id": "account-secret",
                "oai-device-id": "device-secret",
                "oai-session-id": "session-secret",
            },
        }
        for _ in range(604)
    ]
    events.append(
        {
            "kind": "response",
            "phase": "visible_library_file_upload",
            "url": "https://chatgpt.com/backend-api/files/process_upload_stream",
            "body_sample": (
                '{"file_id":"file_00000000111122223333444455556666",'
                '"token":"secret","email":"person@example.com",'
                '"upload_url":"https://example.test/raw?sig=secret&se=later"}'
            ),
            "request_headers": client._protocol_redacted_headers(
                {
                    "accept": "application/json",
                    "chatgpt-account-id": "account-secret",
                    "oai-device-id": "device-secret",
                    "oai-session-id": "session-secret",
                }
            ),
            "extracted_records": [],
        }
    )
    trace = client._public_fetch_xhr_protocol_trace({"installed": True, "events": events})
    assert trace["event_count"] == 605
    assert len(trace["events"]) == 605
    assert trace["trace_truncated"] is False
    assert trace["events"][0]["body_sample"] == ""
    protocol_event = trace["events"][-1]
    assert "file_00000000111122223333444455556666" in protocol_event["body_sample"]
    assert "secret" not in protocol_event["body_sample"]
    assert "person@example.com" not in protocol_event["body_sample"]
    assert "sig=<redacted>" in protocol_event["body_sample"]
    assert "chatgpt-account-id" not in protocol_event["request_headers"]
    assert trace["sensitive_body_fields_redacted"] is True
    assert trace["unrelated_body_samples_omitted"] is True


def test_inventory_discovery_keeps_private_headers_out_of_public_protocol(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    watch = {
        "private_request_headers": {
            7: {
                "authorization": "Bearer private-token",
                "chatgpt-account-id": "private-account",
                "accept": "application/json",
            }
        },
        "events": [
            {
                "kind": "response",
                "sequence": 7,
                "phase": "visible_library_active_inventory",
                "method": "GET",
                "url": "https://chatgpt.com/backend-api/files/library/nodes?q=<redacted>",
                "_raw_url": "https://chatgpt.com/backend-api/files/library/nodes?q=visible.txt",
                "status": 200,
                "request_headers": {"accept": "application/json"},
                "extracted_records": [
                    {
                        "library_metadata_object_id": "libfile_visible",
                        "processed_file_id": "file_visible",
                        "identity_candidates": ["libfile_visible", "file_visible"],
                        "filename": "visible.txt",
                    }
                ],
            }
        ],
    }
    protocol = client._discover_backend_inventory_protocol(
        watch,
        id_candidates=["libfile_visible"],
        filename="visible.txt",
        phases={"visible_library_active_inventory"},
    )
    assert protocol is not None
    assert protocol["_raw_headers"]["authorization"] == "Bearer private-token"
    public = client._public_backend_protocol(protocol)
    assert public is not None
    assert "_raw_headers" not in public
    assert "private-token" not in str(public)
    assert "private-account" not in str(public)


def test_protocol_replay_uses_private_auth_headers_only_in_memory(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    observed = {}

    class FakePage:
        async def evaluate(self, _script, payload):
            observed.update(payload)
            return {
                "ok": True,
                "status": 200,
                "statusText": "OK",
                "url": payload["url"],
                "contentType": "application/json",
                "text": '{"items":[]}',
            }

    result = asyncio.run(
        client._replay_backend_protocol(
            FakePage(),
            protocol={
                "method": "GET",
                "_raw_url": "https://chatgpt.com/backend-api/files/library/nodes?q=visible.txt",
                "_raw_post_data": None,
                "_raw_headers": {
                    "authorization": "Bearer private-token",
                    "chatgpt-account-id": "private-account",
                    "cookie": "private-cookie",
                    "origin": "https://chatgpt.com",
                    "sec-fetch-site": "same-origin",
                    "accept": "application/json",
                },
            },
            mapping={},
            phase="inventory-replay",
        )
    )
    assert result["ok"] is True
    assert observed["headers"]["authorization"] == "Bearer private-token"
    assert observed["headers"]["chatgpt-account-id"] == "private-account"
    assert "cookie" not in observed["headers"]
    assert "origin" not in observed["headers"]
    assert "sec-fetch-site" not in observed["headers"]
    assert "private-token" not in str(result)
    assert "private-account" not in str(result)


def test_exact_inventory_poll_counts_captured_200_as_first_observation(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    libfile_id = "libfile_1234567890abcdef1234567890abcdef"
    calls = 0

    async def fake_replay(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return {
            "ok": True,
            "status": 200,
            "records": [
                {
                    "library_metadata_object_id": libfile_id,
                    "identity_candidates": [libfile_id],
                }
            ],
        }

    class FakePage:
        async def wait_for_timeout(self, _milliseconds: int) -> None:
            return None

    client._replay_backend_protocol = fake_replay  # type: ignore[method-assign]
    result = asyncio.run(
        client._poll_exact_backend_inventory_presence(
            FakePage(),
            protocol={
                "method": "GET",
                "status": 200,
                "exact_identity_observed": True,
                "url": "https://chatgpt.com/backend-api/files/library/nodes?q=<redacted>",
                "_raw_url": "https://chatgpt.com/backend-api/files/library/nodes?q=visible.txt",
            },
            id_candidates=[libfile_id],
            required_stable_observations=2,
            max_attempts=20,
            poll_ms=1,
        )
    )
    assert result["ok"] is True
    assert result["stable_observations"] == 2
    assert calls == 1
    assert result["observations"][0]["attempt"] == 0
    assert result["observations"][0]["source"] == "captured_authenticated_inventory_response"


def test_exact_inventory_poll_fails_fast_on_unauthorized_replay(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    calls = 0

    async def fake_replay(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return {"ok": False, "status": 401, "records": [], "body_sample": "Unauthorized"}

    class FakePage:
        async def wait_for_timeout(self, _milliseconds: int) -> None:
            raise AssertionError("must not wait after 401")

    client._replay_backend_protocol = fake_replay  # type: ignore[method-assign]
    result = asyncio.run(
        client._poll_exact_backend_inventory_presence(
            FakePage(),
            protocol={
                "method": "GET",
                "status": 200,
                "exact_identity_observed": True,
                "url": "https://chatgpt.com/backend-api/files/library/nodes?q=<redacted>",
                "_raw_url": "https://chatgpt.com/backend-api/files/library/nodes?q=visible.txt",
            },
            id_candidates=["libfile_visible"],
            required_stable_observations=2,
            max_attempts=20,
            poll_ms=1,
        )
    )
    assert result["ok"] is False
    assert result["status"] == "backend_inventory_replay_unauthorized"
    assert result["http_status"] == 401
    assert result["stable_observations"] == 1
    assert calls == 1


def test_library_filename_reconstruction_accepts_wrapped_exact_name(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    expected = "pb-library-visible-cb4583bf48.txt"
    assert client._reconstruct_exact_library_filename(
        expected_filename=expected,
        candidates=["pb-library-visibl e-cb4583bf48 .txt Today 71 B"],
    ) == expected


def test_library_filename_reconstruction_rejects_suffix_partial_and_prefix(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    expected = "release.zip"
    assert client._reconstruct_exact_library_filename(
        expected_filename=expected,
        candidates=["release (1).zip Today 71 B", ".zip", "release.zip.bak Today"],
    ) is None


def test_library_snapshot_reconstructs_exact_name_from_rendered_fragments(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    expected = "pb-library-visible-cb4583bf48.txt"

    class Page:
        async def evaluate(self, _script, _expected):
            return [
                {
                    "file_id": "",
                    "filename": "",
                    "filename_candidates": ["Library New"],
                    "text": "Library New",
                    "file_row_candidate": False,
                },
                {
                    "file_id": "",
                    "filename": "",
                    "filename_candidates": ["All Images Files"],
                    "text": "All Images Files",
                    "file_row_candidate": False,
                },
                {
                    "file_id": "",
                    "filename": "",
                    "filename_candidates": ["Name Modified Size"],
                    "text": "Name Modified Size",
                    "file_row_candidate": False,
                },
                {
                    "file_id": "",
                    "filename": ".txt",
                    "filename_candidates": ["pb-library-visibl e-cb4583bf48 .txt Today 71 B"],
                    "text": "pb-library-visibl e-cb4583bf48 .txt Today 71 B",
                    "project_ids": [],
                    "project_references_known": False,
                    "deleted": False,
                    "file_row_candidate": True,
                    "actionable_library_row": True,
                    "action_menu_count": 1,
                    "row_binding_key": "pb-library-row-1",
                },
            ]

    records = asyncio.run(client._snapshot_library_file_cards(Page(), canonical_name=expected))
    assert len(records) == 1
    assert records[0]["filename"] == expected
    assert records[0]["filename_reconstruction"] == "exact_canonical_from_filename_leaf"
    assert records[0]["row_binding_key"] == "pb-library-row-1"
    assert "filename_candidates" not in records[0]


def test_exact_library_ui_binding_requires_one_exact_ui_and_backend_target(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    filename = "pb-library-visible-cb4583bf48.txt"
    libfile = "libfile_d5a56b8829ac8191a9e1fba45dafc254"
    surface = {
        "ok": True,
        "authoritative": True,
        "records": [{
            "file_id": "",
            "filename": filename,
            "project_ids": [],
            "project_references_known": False,
            "deleted": False,
            "file_row_candidate": True,
            "actionable_library_row": True,
            "action_menu_count": 1,
            "row_binding_key": "pb-library-row-1",
        }]
    }
    backend = {
        "ok": True,
        "observations": [
            {"response": {"records": [{
                "file_id": "file_00000000ecfc71f494d05513262f1f62",
                "processed_file_id": "file_00000000ecfc71f494d05513262f1f62",
                "library_metadata_object_id": libfile,
                "identity_candidates": [libfile, "file_00000000ecfc71f494d05513262f1f62"],
                "filename": filename,
            }]}},
            {"response": {"records": [{
                "file_id": "file_00000000ecfc71f494d05513262f1f62",
                "processed_file_id": "file_00000000ecfc71f494d05513262f1f62",
                "library_metadata_object_id": libfile,
                "identity_candidates": [libfile, "file_00000000ecfc71f494d05513262f1f62"],
                "filename": filename,
            }]}},
        ]
    }
    result = client._validate_exact_library_ui_binding(
        surface=surface,
        backend_presence=backend,
        filename=filename,
        library_metadata_object_id=libfile,
    )
    assert result["ok"] is True
    assert result["status"] == "exact_library_file_row_bound"
    assert result["row_binding_key"] == "pb-library-row-1"
    assert result["exact_ui_record_count"] == 1
    assert result["suffix_ui_record_count"] == 0
    assert result["backend_target_record_count"] == 1


def test_exact_library_ui_binding_rejects_unreconstructed_and_suffix_ambiguity(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    filename = "release.zip"
    libfile = "libfile_target12345678"
    backend = {
        "observations": [{
            "response": {
                "records": [{
                    "file_id": "file_target12345678",
                    "library_metadata_object_id": libfile,
                    "identity_candidates": [libfile, "file_target12345678"],
                    "filename": filename,
                }]
            }
        }]
    }
    missing = client._validate_exact_library_ui_binding(
        surface={"ok": True, "authoritative": True, "records": [{"file_id": "", "filename": ".zip", "file_row_candidate": True, "actionable_library_row": True, "action_menu_count": 1, "row_binding_key": "row-missing"}]},
        backend_presence=backend,
        filename=filename,
        library_metadata_object_id=libfile,
    )
    assert missing["status"] == "library_filename_leaf_not_found"

    ambiguous = client._validate_exact_library_ui_binding(
        surface={"ok": True, "authoritative": True, "records": [
            {"file_id": "", "filename": filename, "file_row_candidate": True, "actionable_library_row": True, "action_menu_count": 1, "row_binding_key": "row-exact"},
            {"file_id": "", "filename": "release (1).zip", "file_row_candidate": True, "actionable_library_row": True, "action_menu_count": 1, "row_binding_key": "row-suffix"},
        ]},
        backend_presence=backend,
        filename=filename,
        library_metadata_object_id=libfile,
    )
    assert ambiguous["status"] == "library_file_row_ambiguous"


def test_disposable_delete_refuses_unproven_ui_binding(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    result = asyncio.run(client._delete_disposable_library_file_via_ui(
        object(),
        filename="release.zip",
        delete_forever=False,
        ui_binding={"ok": False, "status": "library_actionable_row_ambiguous"},
    ))
    assert result["ok"] is False
    assert result["status"] == "exact_library_ui_binding_required"


def test_exact_library_ui_binding_requires_unique_row_menu(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    filename = "release.zip"
    libfile = "libfile_target12345678"
    backend = {
        "observations": [{
            "response": {
                "records": [{
                    "file_id": "file_target12345678",
                    "library_metadata_object_id": libfile,
                    "identity_candidates": [libfile, "file_target12345678"],
                    "filename": filename,
                }]
            }
        }]
    }
    result = client._validate_exact_library_ui_binding(
        surface={"ok": True, "authoritative": True, "records": [{
            "file_id": "",
            "filename": filename,
            "file_row_candidate": True,
            "actionable_library_row": False,
            "action_menu_count": 2,
            "row_binding_key": "row-1",
        }]},
        backend_presence=backend,
        filename=filename,
        library_metadata_object_id=libfile,
    )
    assert result["ok"] is True
    assert result["status"] == "exact_library_file_row_bound"
    assert result["pre_hover_menu_count"] == 0


def test_disposable_delete_uses_only_row_scoped_menu(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    clicked: list[str] = []

    class Item:
        def __init__(self, name: str):
            self.name = name

        async def is_visible(self):
            return True

    class LocatorList:
        def __init__(self, items):
            self.items = list(items)

        async def count(self):
            return len(self.items)

        def nth(self, index):
            return self.items[index]

    menu = Item("row-menu")
    action = Item("delete-action")

    class Row:
        async def hover(self):
            return None

        def locator(self, selector):
            assert 'aria-haspopup="menu"' in selector
            return LocatorList([menu])

    class Page:
        def locator(self, selector):
            if '[role="menu"]' in selector:
                return LocatorList([action])
            if '[role="dialog"]' in selector or 'dialog[open]' in selector:
                return LocatorList([])
            raise AssertionError(f"unexpected page-level selector: {selector}")

        async def wait_for_timeout(self, _ms):
            return None

    async def fake_find(*_args, **_kwargs):
        return Row()

    async def fake_click(locator, *, label: str, **_kwargs):
        clicked.append(f"{getattr(locator, 'name', 'unknown')}:{label}")

    client._find_disposable_library_file_card_by_filename = fake_find  # type: ignore[method-assign]
    client._click_locator_with_fallback = fake_click  # type: ignore[method-assign]
    result = asyncio.run(client._delete_disposable_library_file_via_ui(
        Page(),
        filename="release.zip",
        delete_forever=False,
        ui_binding={
            "ok": True,
            "status": "exact_library_file_row_bound",
            "row_binding_key": "pb-library-row-1",
        },
    ))
    assert result["ok"] is False
    assert result["status"] == "delete_confirmation_not_observed"
    assert result["delete_action_clicked"] is True
    assert result["confirmation_observed"] is False
    assert result["confirmation_clicked"] is False
    assert result["row_scoped_menu_binding"] is True
    assert clicked == [
        "row-menu:library-disposable-row-options",
        "delete-action:library-disposable-delete-action",
    ]


def test_disposable_delete_waits_for_delayed_unique_confirmation(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    clicked: list[str] = []
    state = {"surface_polls": 0, "delete_clicked": False}

    class Item:
        def __init__(self, name: str, text: str = ""):
            self.name = name
            self.text = text

        async def is_visible(self):
            return True

        async def inner_text(self):
            return self.text

        async def get_attribute(self, _name):
            return None

    class LocatorList:
        def __init__(self, items):
            self.items = list(items)

        async def count(self):
            return len(self.items)

        def nth(self, index):
            return self.items[index]

    menu = Item("row-menu")
    action = Item("delete-action", "Delete")
    confirm = Item("delete-confirm", "Delete")

    class Surface(Item):
        def locator(self, selector):
            assert selector == 'button, [role="button"]'
            return LocatorList([confirm])

    surface = Surface("confirm-surface")

    class Row:
        async def hover(self):
            return None

        def locator(self, selector):
            assert 'aria-haspopup="menu"' in selector
            return LocatorList([menu])

    class Page:
        def locator(self, selector):
            if '[role="menu"]' in selector:
                return LocatorList([action])
            if selector == '[role="dialog"], [role="alertdialog"], dialog[open]':
                state["surface_polls"] += 1
                if state["delete_clicked"] and state["surface_polls"] >= 3:
                    return LocatorList([surface])
                return LocatorList([])
            raise AssertionError(f"unexpected page-level selector: {selector}")

        async def wait_for_timeout(self, _ms):
            return None

    async def fake_find(*_args, **_kwargs):
        return Row()

    async def fake_click(locator, *, label: str, **_kwargs):
        clicked.append(f"{getattr(locator, 'name', 'unknown')}:{label}")
        if getattr(locator, "name", "") == "delete-action":
            state["delete_clicked"] = True

    client._find_disposable_library_file_card_by_filename = fake_find  # type: ignore[method-assign]
    client._click_locator_with_fallback = fake_click  # type: ignore[method-assign]
    result = asyncio.run(client._delete_disposable_library_file_via_ui(
        Page(),
        filename="release.zip",
        delete_forever=False,
        ui_binding={
            "ok": True,
            "status": "exact_library_file_row_bound",
            "row_binding_key": "pb-library-row-1",
        },
    ))
    assert result["ok"] is True
    assert result["status"] == "delete_confirmation_clicked"
    assert result["delete_action_clicked"] is True
    assert result["confirmation_observed"] is True
    assert result["confirmation_clicked"] is True
    assert result["confirmation_observations"] >= 3
    assert clicked == [
        "row-menu:library-disposable-row-options",
        "delete-action:library-disposable-delete-action",
        "delete-confirm:library-disposable-delete-confirm",
    ]


def test_exact_library_ui_binding_preserves_non_authoritative_surface_reason(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    result = client._validate_exact_library_ui_binding(
        surface={
            "ok": False,
            "authoritative": False,
            "reason": "library_surface_not_authoritative",
            "records": [],
        },
        backend_presence={"ok": True, "observations": []},
        filename="release.zip",
        library_metadata_object_id="libfile_target12345678",
    )
    assert result["ok"] is False
    assert result["status"] == "library_surface_not_authoritative_after_backend_presence"
    assert result["surface_reason"] == "library_surface_not_authoritative"


def test_disposable_delete_fails_when_hover_does_not_reveal_row_menu(tmp_path: Path) -> None:
    client = browser_client(tmp_path)

    class EmptyLocatorList:
        async def count(self):
            return 0

        def nth(self, index):  # pragma: no cover - defensive
            raise IndexError(index)

    class Row:
        async def hover(self):
            return None

        async def scroll_into_view_if_needed(self):
            return None

        def locator(self, _selector):
            return EmptyLocatorList()

    class Page:
        async def wait_for_timeout(self, _ms):
            return None

    async def fake_find(*_args, **_kwargs):
        return Row()

    client._find_disposable_library_file_card_by_filename = fake_find  # type: ignore[method-assign]
    result = asyncio.run(client._delete_disposable_library_file_via_ui(
        Page(),
        filename="release.zip",
        delete_forever=False,
        ui_binding={
            "ok": True,
            "status": "exact_library_file_row_bound",
            "row_binding_key": "pb-library-row-1",
        },
    ))
    assert result["ok"] is False
    assert result["status"] == "library_row_menu_not_available_after_hover"
    assert result["pre_hover_menu_count"] == 0
    assert result["post_hover_menu_count"] == 0


def test_library_surface_stops_after_bounded_identical_non_authoritative_observations(tmp_path: Path) -> None:
    client = browser_client(tmp_path)

    class Page:
        async def wait_for_timeout(self, milliseconds: int):
            await asyncio.sleep(milliseconds / 1000)

    async def fake_route(*_args, **_kwargs):
        return {
            "current_url": "https://chatgpt.com/library?search=release.zip",
            "route_ok": True,
            "app_loaded": True,
            "loading_visible": False,
            "surface_kind": "active",
            "surface_active": True,
            "ready": True,
        }

    async def fake_snapshot(*_args, **_kwargs):
        return []

    async def fake_empty(*_args, **_kwargs):
        return False

    client._library_route_state = fake_route  # type: ignore[method-assign]
    client._snapshot_library_file_cards = fake_snapshot  # type: ignore[method-assign]
    client._library_empty_state_visible = fake_empty  # type: ignore[method-assign]
    result = asyncio.run(client._wait_for_authoritative_library_family_surface(
        Page(),
        canonical_name="release.zip",
        label="bounded-non-authoritative",
        timeout_ms=30_000,
        poll_ms=1,
        max_identical_non_authoritative_observations=5,
    ))
    assert result["ok"] is False
    assert result["reason"] == "library_surface_not_authoritative"
    assert result["bounded_identical_state_stop"] is True
    assert result["identical_non_authoritative_observations"] == 5
    assert len(result["observations"]) == 5


def test_delete_protocol_pairs_exact_request_with_successful_response(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    watch = {
        "private_request_headers": {7: {"authorization": "Bearer private", "chatgpt-account-id": "acct"}},
        "events": [
            {
                "kind": "request",
                "sequence": 7,
                "phase": "visible_library_soft_delete",
                "method": "PATCH",
                "url": "https://chatgpt.com/backend-api/files/library/nodes/libfile_target",
                "headers": {"content-type": "application/json"},
                "post_data_sample": '{"trashed":true}',
                "_raw_url": "https://chatgpt.com/backend-api/files/library/nodes/libfile_target",
                "_raw_post_data": '{"trashed":true}',
                "_raw_headers": {"content-type": "application/json"},
            },
            {
                "kind": "response",
                "sequence": 7,
                "phase": "visible_library_soft_delete",
                "method": "PATCH",
                "url": "https://chatgpt.com/backend-api/files/library/nodes/libfile_target",
                "status": 204,
                "_raw_url": "https://chatgpt.com/backend-api/files/library/nodes/libfile_target",
                "_raw_body": "",
            },
        ],
    }
    protocol = client._discover_backend_delete_protocol(
        watch,
        id_candidates=["libfile_target"],
        filename="visible.txt",
        phase="visible_library_soft_delete",
    )
    assert protocol is not None
    assert protocol["method"] == "PATCH"
    assert protocol["status"] == 204
    assert protocol["response_proven_successful"] is True
    assert protocol["_raw_headers"]["authorization"] == "Bearer private"
    assert "authorization" not in client._public_backend_protocol(protocol)["headers"]


def test_delete_protocol_rejects_exact_request_without_success_response(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    watch = {
        "events": [
            {
                "kind": "request",
                "sequence": 9,
                "phase": "visible_library_soft_delete",
                "method": "DELETE",
                "_raw_url": "https://chatgpt.com/backend-api/files/libfile_target",
                "_raw_post_data": None,
            },
            {
                "kind": "response",
                "sequence": 9,
                "phase": "visible_library_soft_delete",
                "method": "DELETE",
                "status": 500,
                "_raw_url": "https://chatgpt.com/backend-api/files/libfile_target",
                "_raw_body": '{"error":"failed"}',
            },
        ],
    }
    assert client._discover_backend_delete_protocol(
        watch,
        id_candidates=["libfile_target"],
        filename="visible.txt",
        phase="visible_library_soft_delete",
    ) is None


def test_soft_delete_backend_state_accepts_stable_active_absence(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    responses = [
        {"ok": True, "status": 200, "records": []},
        {"ok": True, "status": 200, "records": []},
    ]

    async def replay(*_args, **_kwargs):
        return responses.pop(0)

    class Page:
        async def wait_for_timeout(self, _ms):
            return None

    client._replay_backend_protocol = replay  # type: ignore[method-assign]
    result = asyncio.run(client._poll_exact_backend_inventory_soft_deleted(
        Page(),
        protocol={"method": "GET"},
        id_candidates=["libfile_target"],
        poll_ms=1,
    ))
    assert result["ok"] is True
    assert result["status"] == "exact_library_identity_soft_deleted"
    assert result["proof"] == "absent_from_active_inventory"
    assert result["stable_observations"] == 2


def test_soft_delete_backend_state_accepts_explicit_trashed_record(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    trashed = {
        "library_metadata_object_id": "libfile_target",
        "identity_candidates": ["libfile_target"],
        "deleted": True,
    }

    async def replay(*_args, **_kwargs):
        return {"ok": True, "status": 200, "records": [trashed]}

    class Page:
        async def wait_for_timeout(self, _ms):
            return None

    client._replay_backend_protocol = replay  # type: ignore[method-assign]
    result = asyncio.run(client._poll_exact_backend_inventory_soft_deleted(
        Page(),
        protocol={"method": "GET"},
        id_candidates=["libfile_target"],
        poll_ms=1,
    ))
    assert result["ok"] is True
    assert result["proof"] == "explicitly_trashed"


def test_soft_delete_backend_state_fails_when_exact_record_remains_active(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    active = {
        "library_metadata_object_id": "libfile_target",
        "identity_candidates": ["libfile_target"],
        "deleted": False,
    }

    async def replay(*_args, **_kwargs):
        return {"ok": True, "status": 200, "records": [active]}

    class Page:
        async def wait_for_timeout(self, _ms):
            return None

    client._replay_backend_protocol = replay  # type: ignore[method-assign]
    result = asyncio.run(client._poll_exact_backend_inventory_soft_deleted(
        Page(),
        protocol={"method": "GET"},
        id_candidates=["libfile_target"],
        max_attempts=2,
        poll_ms=1,
    ))
    assert result["ok"] is False
    assert result["status"] == "soft_delete_backend_state_not_verified"


def test_recently_deleted_navigation_proves_active_surface(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    clicked: list[str] = []

    class Control:
        pass

    class EmptyList:
        async def count(self):
            return 0

        def nth(self, index):  # pragma: no cover
            raise IndexError(index)

    class Page:
        async def evaluate(self, _script):
            return []

        def locator(self, _selector):
            return EmptyList()

        async def wait_for_timeout(self, _ms):
            return None

    async def find(*_args, **_kwargs):
        return Control()

    async def click(_locator, *, label: str, **_kwargs):
        clicked.append(label)

    async def route(*_args, **_kwargs):
        return {
            "current_url": "https://chatgpt.com/library?view=trash",
            "route_ok": True,
            "app_loaded": True,
            "loading_visible": False,
            "surface_kind": "recently_deleted",
            "surface_active": True,
            "ready": True,
        }

    client._find_visible_locator = find  # type: ignore[method-assign]
    client._click_locator_with_fallback = click  # type: ignore[method-assign]
    client._library_route_state = route  # type: ignore[method-assign]
    result = asyncio.run(client._open_library_recently_deleted(Page()))
    assert result["ok"] is True
    assert result["status"] == "recently_deleted_surface_active"
    assert clicked == ["library-recently-deleted"]


def test_diagnostic_operation_exposes_processing_stream_timeout_reason(tmp_path: Path) -> None:
    client = browser_client(tmp_path)

    async def fake_ensure_logged_in(_page, _context):
        return None

    async def fake_create_project_operation(**_kwargs):
        from promptbranch_browser_auth.exceptions import ResponseTimeoutError
        raise ResponseTimeoutError(
            "project_source_processing_stream_timeout: expected_filename=release.zip"
        )

    client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    client._create_project_operation = fake_create_project_operation  # type: ignore[method-assign]

    result = asyncio.run(
        client._library_backend_protocol_reupload_diagnostic_operation(
            context=object(),
            page=object(),
            project_name_prefix="itest",
        )
    )

    assert result["status"] == "diagnostic_completed"
    assert result["conclusion"] == "diagnostic_inconclusive"
    assert result["reason"] == "project_source_processing_stream_timeout"
    assert result["error_type"] == "ResponseTimeoutError"


def test_diagnostic_finalizer_returns_structured_json_when_trace_settlement_times_out(tmp_path: Path) -> None:
    client = browser_client(tmp_path)

    async def fake_ensure_logged_in(_page, _context):
        return None

    async def fake_create_project_operation(**_kwargs):
        return {"ok": False, "project_url": None}

    async def fake_settle(_watch, **_kwargs):
        return {
            "ok": False,
            "status": "fetch_xhr_protocol_watch_settle_timeout",
            "task_count": 2,
            "completed_task_count": 1,
            "cancelled_task_count": 1,
            "failed_task_count": 0,
            "pending_task_count": 1,
            "detached_task_count": 0,
            "unresolved_tasks": [
                {
                    "task_kind": "response_capture",
                    "phase": "project_create",
                    "method": "GET",
                    "resource_type": "fetch",
                    "url": "https://chatgpt.com/backend-api/files/library",
                    "content_type": "application/json",
                }
            ],
        }

    client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    client._create_project_operation = fake_create_project_operation  # type: ignore[method-assign]
    client._settle_fetch_xhr_protocol_watch = fake_settle  # type: ignore[method-assign]

    result = asyncio.run(
        client._library_backend_protocol_reupload_diagnostic_operation(
            context=object(),
            page=object(),
            project_name_prefix="itest",
        )
    )

    assert result["status"] == "diagnostic_completed"
    assert result["conclusion"] == "diagnostic_inconclusive"
    assert result["reason"] == "fetch_xhr_protocol_watch_settle_timeout"
    assert result["reason_before_fetch_xhr_settlement"] == "project_create_failed"
    assert result["error_type"] == "ResponseTimeoutError"
    assert result["fetch_xhr_trace"]["task_settlement"]["pending_task_count"] == 1


def test_real_diagnostic_caller_rejects_pending_stream_without_result(tmp_path: Path) -> None:
    client = browser_client(tmp_path)

    async def fake_ensure_logged_in(_page, _context):
        return None

    async def fake_create_project_operation(**_kwargs):
        return {
            "ok": True,
            "project_url": "https://chatgpt.com/g/g-p-diagnostic/project",
        }

    async def fake_legacy_upload(**_kwargs):
        return {
            "ok": False,
            "status": "post_commit_source_surface_not_refreshed",
            "save_request_quiet": {
                "processing_stream_pending": True,
                "quiet_reason": "ordinary_save_quiet_processing_stream_pending",
            },
            "processing_stream": None,
            "save_request_summary": {},
        }

    async def should_not_poll(*_args, **_kwargs):
        raise AssertionError("source persistence polling must not run after invariant failure")

    async def fake_settle(_watch, **_kwargs):
        return None

    client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    client._create_project_operation = fake_create_project_operation  # type: ignore[method-assign]
    client._add_project_source_operation_legacy_10_75 = fake_legacy_upload  # type: ignore[method-assign]
    client._browser_poll_project_source_family_state = should_not_poll  # type: ignore[method-assign]
    client._install_fetch_xhr_protocol_watch = lambda _context: {"installed": False, "events": []}  # type: ignore[method-assign]
    client._set_fetch_xhr_protocol_phase = lambda *_args, **_kwargs: None  # type: ignore[method-assign]
    client._settle_fetch_xhr_protocol_watch = fake_settle  # type: ignore[method-assign]
    client._dispose_fetch_xhr_protocol_watch = lambda *_args, **_kwargs: None  # type: ignore[method-assign]
    client._public_fetch_xhr_protocol_trace = lambda _watch: {  # type: ignore[method-assign]
        "installed": False,
        "event_count": 0,
        "trace_truncated": False,
        "sensitive_headers_redacted": True,
        "sensitive_body_fields_redacted": True,
    }

    result = asyncio.run(
        client._library_backend_protocol_reupload_diagnostic_operation(
            context=object(),
            page=object(),
            project_name_prefix="itest",
        )
    )

    assert result["status"] == "diagnostic_completed"
    assert result["conclusion"] == "diagnostic_inconclusive"
    assert result["reason"] == "internal_processing_stream_wait_skipped"
    assert result["first_upload_processing_invariant"]["ok"] is False
    assert result["first_upload"]["upload_response"]["processing_stream"] is None


def test_visible_library_processing_stream_returns_exact_terminal_identity(tmp_path: Path) -> None:
    client = browser_client(tmp_path)

    class Page:
        async def wait_for_timeout(self, _ms):
            return None

    watch = {
        "processing_stream_started": 1,
        "processing_stream_finished": 1,
        "processing_stream_failed": 0,
        "processing_stream_response_tasks": [],
        "processing_stream_terminal": {
            "status": "completed",
            "terminal_event": "file.processing.completed",
            "terminal_message": "done",
            "processed_file_id": "file_00000000111122223333444455556666",
            "library_metadata_object_id": "libfile_visible",
            "library_file_name": "visible.txt",
            "expected_filename": "visible.txt",
            "events": [
                "file.processing.started",
                "file.processing.file_ready",
                "file.indexing.completed",
                "file.processing.completed",
            ],
            "identity_verified": True,
        },
    }

    result = asyncio.run(
        client._wait_for_visible_library_processing_stream(
            Page(),
            watch,
            expected_filename="visible.txt",
            timeout_ms=50,
            poll_interval_ms=1,
        )
    )

    assert result["ok"] is True
    assert result["status"] == "visible_library_processing_stream_completed"
    assert result["processed_file_id"] == "file_00000000111122223333444455556666"
    assert result["library_metadata_object_id"] == "libfile_visible"
    assert result["library_file_name"] == "visible.txt"


def test_visible_library_processing_stream_rejects_incomplete_terminal_identity(tmp_path: Path) -> None:
    client = browser_client(tmp_path)

    class Page:
        async def wait_for_timeout(self, _ms):
            return None

    watch = {
        "processing_stream_started": 1,
        "processing_stream_finished": 1,
        "processing_stream_failed": 0,
        "processing_stream_response_tasks": [],
        "processing_stream_terminal": {
            "status": "completed",
            "terminal_event": "file.processing.completed",
            "terminal_message": "done",
            "processed_file_id": "file_00000000111122223333444455556666",
            "library_metadata_object_id": None,
            "library_file_name": "visible.txt",
            "expected_filename": "visible.txt",
            "events": ["file.processing.completed"],
            "identity_verified": False,
        },
    }

    result = asyncio.run(
        client._wait_for_visible_library_processing_stream(
            Page(),
            watch,
            expected_filename="visible.txt",
            timeout_ms=50,
            poll_interval_ms=1,
        )
    )

    assert result["ok"] is False
    assert result["status"] == "visible_library_processing_stream_identity_not_verified"
    assert result["library_metadata_object_id"] is None


def test_real_diagnostic_uses_dedicated_visible_library_stream_identity(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    calls: list[str] = []

    class Page:
        async def wait_for_timeout(self, _ms):
            return None

    async def fake_ensure_logged_in(_page, _context):
        return None

    async def fake_create_project_operation(**_kwargs):
        return {"ok": True, "project_url": "https://chatgpt.com/g/g-p-diagnostic/project"}

    async def fake_legacy_upload(**_kwargs):
        return {
            "ok": True,
            "save_request_quiet": {
                "processing_stream_pending": True,
                "quiet_reason": "ordinary_save_quiet_processing_stream_pending",
            },
            "processing_stream": {
                "status": "project_source_processing_stream_completed",
                "processed_file_id": "file_00000000aaaaaaaaaaaaaaaaaaaaaaaa",
                "library_metadata_object_id": "libfile_project",
                "library_file_name": _kwargs["display_name"],
                "terminal_event": "file.processing.completed",
            },
            "save_request_summary": {},
        }

    presence_calls = 0

    async def fake_presence(*_args, **kwargs):
        nonlocal presence_calls
        presence_calls += 1
        if kwargs.get("expect_present"):
            return {"ok": True, "exact_source_name": kwargs["requested_filename"]}
        return {"ok": True}

    async def fake_remove(**_kwargs):
        return {"ok": True}

    async def fake_goto(*_args, **_kwargs):
        return None

    async def fake_upload(*_args, **_kwargs):
        calls.append("visible_upload")
        return {"ok": False, "status": "library_disposable_upload_not_verified"}

    stream_watch = {"installed": True}

    def fake_install_stream(*_args, **_kwargs):
        calls.append("stream_watch_installed")
        return stream_watch

    async def fake_wait_stream(*_args, **_kwargs):
        calls.append("stream_waited")
        assert _args[1] is stream_watch
        return {
            "ok": True,
            "status": "visible_library_processing_stream_completed",
            "processed_file_id": "file_00000000111122223333444455556666",
            "library_metadata_object_id": "libfile_visible",
            "library_file_name": "pb-library-visible-test.txt",
            "terminal_event": "file.processing.completed",
            "events": ["file.processing.completed"],
        }

    def fake_dispose_stream(*_args, **_kwargs):
        calls.append("stream_watch_disposed")

    async def fake_settle(_watch, **_kwargs):
        return {
            "ok": True,
            "status": "fetch_xhr_protocol_watch_settled",
            "task_count": 0,
            "completed_task_count": 0,
            "cancelled_task_count": 0,
            "failed_task_count": 0,
            "pending_task_count": 0,
            "detached_task_count": 0,
            "unresolved_tasks": [],
        }

    client.ensure_logged_in = fake_ensure_logged_in  # type: ignore[method-assign]
    client._create_project_operation = fake_create_project_operation  # type: ignore[method-assign]
    client._add_project_source_operation_legacy_10_75 = fake_legacy_upload  # type: ignore[method-assign]
    client._browser_poll_project_source_family_state = fake_presence  # type: ignore[method-assign]
    client._remove_project_source_operation = fake_remove  # type: ignore[method-assign]
    client._goto = fake_goto  # type: ignore[method-assign]
    client._upload_disposable_library_file_via_ui = fake_upload  # type: ignore[method-assign]
    client._install_visible_library_processing_stream_watch = fake_install_stream  # type: ignore[method-assign]
    client._wait_for_visible_library_processing_stream = fake_wait_stream  # type: ignore[method-assign]
    client._dispose_visible_library_processing_stream_watch = fake_dispose_stream  # type: ignore[method-assign]
    client._settle_fetch_xhr_protocol_watch = fake_settle  # type: ignore[method-assign]
    client._library_search_exact_family = fake_goto  # type: ignore[method-assign]
    client._discover_backend_inventory_protocol = lambda *_args, **_kwargs: None  # type: ignore[method-assign]
    client._install_fetch_xhr_protocol_watch = lambda _context: {  # type: ignore[method-assign]
        "installed": False,
        "events": [],
        "phase": "initial",
        "settlement_history": [],
    }
    client._set_fetch_xhr_protocol_phase = lambda watch, phase: watch.update({"phase": phase})  # type: ignore[method-assign]
    client._dispose_fetch_xhr_protocol_watch = lambda *_args, **_kwargs: None  # type: ignore[method-assign]
    client._public_fetch_xhr_protocol_trace = lambda _watch: {  # type: ignore[method-assign]
        "installed": False,
        "event_count": 0,
        "trace_truncated": False,
        "sensitive_headers_redacted": True,
        "sensitive_body_fields_redacted": True,
    }

    result = asyncio.run(
        client._library_backend_protocol_reupload_diagnostic_operation(
            context=object(),
            page=Page(),
            project_name_prefix="itest",
        )
    )

    assert result["reason"] == "active_inventory_endpoint_not_discovered"
    assert result["visible_library_upload_processing_stream"]["ok"] is True
    assert result["visible_library_identity"]["processed_file_id"] == "file_00000000111122223333444455556666"
    assert result["visible_library_identity"]["library_metadata_object_id"] == "libfile_visible"
    assert calls == [
        "stream_watch_installed",
        "visible_upload",
        "stream_waited",
        "stream_watch_disposed",
    ]
    assert presence_calls == 2


def test_fetch_xhr_protocol_watch_keeps_immutable_request_phase_on_response(tmp_path: Path) -> None:
    client = browser_client(tmp_path)

    class Context:
        def __init__(self) -> None:
            self.handlers = {}

        def on(self, name, handler) -> None:
            self.handlers[name] = handler

    class Request:
        resource_type = "fetch"
        method = "PATCH"
        url = "https://chatgpt.com/backend-api/files/library/nodes/libfile_target"
        headers = {"content-type": "application/json"}
        post_data = '{"trashed":true}'

    class Response:
        status = 204
        url = Request.url

        def __init__(self, request) -> None:
            self.request = request

        async def all_headers(self):
            return {"content-type": "application/json"}

        async def text(self):
            return ""

    async def scenario() -> dict:
        context = Context()
        watch = client._install_fetch_xhr_protocol_watch(context)
        client._set_fetch_xhr_protocol_phase(watch, "visible_library_active_inventory")
        request = Request()
        context.handlers["request"](request)
        client._set_fetch_xhr_protocol_phase(watch, "visible_library_soft_delete")
        context.handlers["response"](Response(request))
        await client._settle_fetch_xhr_protocol_watch(watch)
        return watch

    watch = asyncio.run(scenario())
    request_event = next(event for event in watch["events"] if event.get("kind") == "request")
    response_event = next(event for event in watch["events"] if event.get("kind") == "response")
    assert request_event["phase"] == "visible_library_active_inventory"
    assert request_event["request_phase"] == "visible_library_active_inventory"
    assert response_event["phase"] == "visible_library_active_inventory"
    assert response_event["request_phase"] == "visible_library_active_inventory"
    assert response_event["response_observed_phase"] == "visible_library_soft_delete"
    assert response_event["sequence"] == request_event["sequence"]


def test_delete_protocol_sequence_boundary_is_authoritative_over_phase(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    watch = {
        "private_request_headers": {8: {"authorization": "Bearer private"}},
        "events": [
            {
                "kind": "request",
                "sequence": 4,
                "phase": "visible_library_active_inventory",
                "request_phase": "visible_library_active_inventory",
                "method": "PATCH",
                "_raw_url": "https://chatgpt.com/backend-api/files/library/nodes/libfile_target",
                "_raw_post_data": '{"trashed":true}',
            },
            {
                "kind": "response",
                "sequence": 4,
                "phase": "visible_library_active_inventory",
                "request_phase": "visible_library_active_inventory",
                "method": "PATCH",
                "status": 204,
                "_raw_url": "https://chatgpt.com/backend-api/files/library/nodes/libfile_target",
                "_raw_body": "",
            },
            {
                "kind": "request",
                "sequence": 8,
                "phase": "visible_library_active_inventory",
                "request_phase": "visible_library_active_inventory",
                "method": "PATCH",
                "_raw_url": "https://chatgpt.com/backend-api/files/library/nodes/libfile_target",
                "_raw_post_data": '{"trashed":true}',
            },
            {
                "kind": "response",
                "sequence": 8,
                "phase": "visible_library_active_inventory",
                "request_phase": "visible_library_active_inventory",
                "response_observed_phase": "visible_library_soft_delete",
                "method": "PATCH",
                "status": 204,
                "_raw_url": "https://chatgpt.com/backend-api/files/library/nodes/libfile_target",
                "_raw_body": "",
            },
        ],
    }
    result = client._discover_backend_delete_protocol_result(
        watch,
        id_candidates=["libfile_target"],
        filename="visible.txt",
        phase="visible_library_soft_delete",
        sequence_after=7,
    )
    assert result["ok"] is True
    assert result["status"] == "soft_delete_protocol_discovered"
    assert result["protocol"]["sequence"] == 8
    assert result["protocol"]["sequence_after"] == 7
    assert result["protocol"]["phase"] == "visible_library_active_inventory"
    assert result["protocol"]["response_observed_phase"] == "visible_library_soft_delete"


def test_delete_protocol_sequence_boundary_reports_identity_not_verified(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    watch = {
        "events": [
            {
                "kind": "request",
                "sequence": 12,
                "phase": "visible_library_soft_delete",
                "request_phase": "visible_library_soft_delete",
                "method": "POST",
                "_raw_url": "https://chatgpt.com/backend-api/files/library/nodes/delete",
                "_raw_post_data": '{"trashed":true}',
                "_raw_headers": {"content-type": "application/json"},
            },
            {
                "kind": "response",
                "sequence": 12,
                "phase": "visible_library_soft_delete",
                "request_phase": "visible_library_soft_delete",
                "method": "POST",
                "status": 200,
                "content_type": "application/json",
                "_raw_url": "https://chatgpt.com/backend-api/files/library/nodes/delete",
                "_raw_body": '{"ok":true}',
            },
        ]
    }
    result = client._discover_backend_delete_protocol_result(
        watch,
        id_candidates=["libfile_target", "file_target"],
        filename="visible.txt",
        phase="visible_library_soft_delete",
        sequence_after=11,
    )
    assert result["ok"] is False
    assert result["status"] == "soft_delete_protocol_identity_not_verified"
    assert result["protocol"] is None
    assert len(result["mutation_candidates"]) == 1
    candidate = result["mutation_candidates"][0]
    assert candidate["sequence"] == 12
    assert candidate["url_path"] == "/backend-api/files/library/nodes/delete"
    assert candidate["status"] == 200
    assert candidate["exact_identity_observed"] is False
    assert candidate["request_body_schema"]["format"] == "json"
    assert candidate["response_body_schema"]["format"] == "json"


def test_fetch_xhr_settlement_history_deduplicates_unchanged_phase_and_task_count(tmp_path: Path) -> None:
    client = browser_client(tmp_path)

    async def scenario() -> tuple[dict, dict, dict]:
        watch = {
            "phase": "visible_library_soft_delete",
            "tasks": [],
            "task_metadata": {},
            "settlement_history": [],
        }
        first = await client._settle_fetch_xhr_protocol_watch(watch)
        second = await client._settle_fetch_xhr_protocol_watch(watch)
        return watch, first, second

    watch, first, second = asyncio.run(scenario())
    assert len(watch["settlement_history"]) == 1
    assert first["settlement_index"] == 1
    assert second["settlement_index"] == 1
    assert second["duplicate_history_entry_suppressed"] is True


def test_real_diagnostic_orders_soft_delete_boundary_before_phase_and_click() -> None:
    source = Path(__file__).parents[1].joinpath("promptbranch_browser_auth/client.py").read_text()
    operation = source[source.index("    async def _library_backend_protocol_reupload_diagnostic_operation("):]
    settle_index = operation.index("pre_soft_delete_settlement = await self._settle_fetch_xhr_protocol_watch")
    boundary_index = operation.index("soft_delete_boundary = self._fetch_xhr_protocol_sequence_boundary")
    phase_index = operation.index("self._set_fetch_xhr_protocol_phase(protocol_watch, 'visible_library_soft_delete')")
    click_index = operation.index("visible_soft_delete = await self._delete_disposable_library_file_via_ui")
    discovery_index = operation.index("soft_delete_discovery = self._discover_backend_delete_protocol_result")
    assert settle_index < boundary_index < phase_index < click_index < discovery_index
    assert "sequence_after=int(soft_delete_boundary.get('max_request_sequence') or 0)" in operation


def test_diagnostic_finalizer_does_not_reappend_suppressed_settlement() -> None:
    source = Path(__file__).parents[1].joinpath("promptbranch_browser_auth/client.py").read_text()
    operation = source[source.index("    async def _library_backend_protocol_reupload_diagnostic_operation("):]
    assert "final_settlement.get('duplicate_history_entry_suppressed')" in operation


def test_real_diagnostic_promotes_delete_triggered_only_after_exact_protocol_proof() -> None:
    source = Path(__file__).parents[1].joinpath("promptbranch_browser_auth/client.py").read_text()
    operation = source[source.index("    async def _library_backend_protocol_reupload_diagnostic_operation("):]
    confirmation_missing_index = operation.index("confirmation_not_observed = (")
    discovery_index = operation.index("soft_delete_discovery = self._discover_backend_delete_protocol_result")
    protocol_guard_index = operation.index("if not isinstance(soft_delete_protocol, dict):")
    promotion_index = operation.index("'status': 'delete_triggered'", protocol_guard_index)
    assert confirmation_missing_index < discovery_index < protocol_guard_index < promotion_index
    assert "soft_delete_confirmation_or_direct_mutation_not_observed" in operation
    assert "direct_exact_backend_mutation" in operation
    assert "confirmation_then_exact_backend_mutation" in operation


def test_disposable_delete_helper_never_reports_delete_triggered_without_protocol_proof() -> None:
    source = Path(__file__).parents[1].joinpath("promptbranch_browser_auth/client.py").read_text()
    start = source.index("    async def _delete_disposable_library_file_via_ui(")
    end = source.index("    def _browser_diagnostic_upload_identity", start)
    helper = source[start:end]
    assert "'status': 'delete_confirmation_clicked'" in helper
    assert "'status': 'delete_confirmation_not_observed'" in helper
    assert "'status': 'delete_triggered'" not in helper


def test_library_ui_recovery_succeeds_after_exact_search_reapply(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    calls: list[str] = []

    class Page:
        async def wait_for_timeout(self, _ms):
            return None

    async def fake_reapply(_page, _canonical_name, *, label):
        calls.append(label)
        return {
            "ok": True,
            "status": "library_exact_search_reapplied",
            "search_cleared": True,
            "search_reapplied": True,
        }

    async def fake_wait(_page, **kwargs):
        calls.append(kwargs["label"])
        return {
            "ok": True,
            "authoritative": True,
            "reason": "stable_library_snapshot",
            "records": [{"filename": "visible.txt"}],
            "family_records": [{"filename": "visible.txt"}],
            "observations": [{"observation": 1}, {"observation": 2}],
        }

    client._library_reapply_exact_family_search = fake_reapply  # type: ignore[method-assign]
    client._wait_for_authoritative_library_family_surface = fake_wait  # type: ignore[method-assign]
    result = asyncio.run(client._recover_library_surface_after_backend_presence(
        Page(),
        canonical_name="visible.txt",
        initial_surface={
            "ok": False,
            "reason": "library_surface_not_authoritative",
            "identical_non_authoritative_observations": 5,
            "observations": [{"observation": index} for index in range(1, 6)],
        },
    ))
    assert result["ok"] is True
    assert result["recovery"]["status"] == "library_surface_recovered_after_search_reapply"
    assert result["recovery"]["search_reapplied"] is True
    assert result["recovery"]["page_reloaded"] is False
    assert result["recovery"]["initial_identical_observations"] == 5
    assert calls == [
        "library-backend-presence-recovery-reapply",
        "library-backend-presence-recovery-after-reapply",
    ]


def test_library_ui_recovery_reloads_once_then_recovers(tmp_path: Path) -> None:
    client = browser_client(tmp_path)
    wait_results = [
        {
            "ok": False,
            "authoritative": False,
            "reason": "library_surface_not_authoritative",
            "observations": [{"observation": index} for index in range(1, 6)],
        },
        {
            "ok": True,
            "authoritative": True,
            "reason": "stable_library_snapshot",
            "records": [{"filename": "visible.txt"}],
            "family_records": [{"filename": "visible.txt"}],
            "observations": [{"observation": 1}, {"observation": 2}],
        },
    ]

    class Page:
        def __init__(self):
            self.reload_count = 0

        async def reload(self, *, wait_until):
            assert wait_until == "domcontentloaded"
            self.reload_count += 1

        async def wait_for_timeout(self, _ms):
            return None

    async def fake_reapply(_page, _canonical_name, *, label):
        return {
            "ok": True,
            "status": "library_exact_search_reapplied",
            "search_cleared": True,
            "search_reapplied": True,
            "label": label,
        }

    async def fake_wait(_page, **_kwargs):
        return wait_results.pop(0)

    page = Page()
    client._library_reapply_exact_family_search = fake_reapply  # type: ignore[method-assign]
    client._wait_for_authoritative_library_family_surface = fake_wait  # type: ignore[method-assign]
    result = asyncio.run(client._recover_library_surface_after_backend_presence(
        page,
        canonical_name="visible.txt",
        initial_surface={
            "ok": False,
            "reason": "library_surface_not_authoritative",
            "identical_non_authoritative_observations": 5,
            "observations": [{"observation": index} for index in range(1, 6)],
        },
    ))
    assert result["ok"] is True
    assert result["recovery"]["status"] == "library_surface_recovered_after_reload"
    assert result["recovery"]["reload_attempt_count"] == 1
    assert result["recovery"]["page_reloaded"] is True
    assert result["recovery"]["search_reapplied_after_reload"] is True
    assert result["recovery"]["post_recovery_observation_count"] == 7
    assert page.reload_count == 1
    assert wait_results == []


def test_library_ui_recovery_fails_closed_after_one_reload(tmp_path: Path) -> None:
    client = browser_client(tmp_path)

    class Page:
        def __init__(self):
            self.reload_count = 0

        async def reload(self, *, wait_until):
            assert wait_until == "domcontentloaded"
            self.reload_count += 1

        async def wait_for_timeout(self, _ms):
            return None

    async def fake_reapply(_page, _canonical_name, *, label):
        return {
            "ok": True,
            "status": "library_exact_search_reapplied",
            "search_cleared": True,
            "search_reapplied": True,
            "label": label,
        }

    async def fake_wait(_page, **_kwargs):
        return {
            "ok": False,
            "authoritative": False,
            "reason": "library_surface_not_authoritative",
            "record_count": 0,
            "family_record_count": 0,
            "empty_state_visible": False,
            "identical_non_authoritative_observations": 5,
            "route_state": {"ready": True, "loading_visible": False},
            "observations": [{"observation": index} for index in range(1, 6)],
        }

    page = Page()
    client._library_reapply_exact_family_search = fake_reapply  # type: ignore[method-assign]
    client._wait_for_authoritative_library_family_surface = fake_wait  # type: ignore[method-assign]
    result = asyncio.run(client._recover_library_surface_after_backend_presence(
        page,
        canonical_name="visible.txt",
        initial_surface={
            "ok": False,
            "reason": "library_surface_not_authoritative",
            "identical_non_authoritative_observations": 5,
            "observations": [{"observation": index} for index in range(1, 6)],
        },
    ))
    assert result["ok"] is False
    assert result["recovery"]["status"] == "library_surface_not_authoritative_after_bounded_recovery"
    assert result["recovery"]["reload_attempt_count"] == 1
    assert result["recovery"]["page_reloaded"] is True
    assert page.reload_count == 1


def test_real_diagnostic_recovers_library_ui_before_delete_boundary() -> None:
    source = Path(__file__).parents[1].joinpath("promptbranch_browser_auth/client.py").read_text()
    operation = source[source.index("    async def _library_backend_protocol_reupload_diagnostic_operation("):]
    initial_wait_index = operation.index("visible_surface = await self._wait_for_authoritative_library_family_surface")
    recovery_index = operation.index("recovery_result = await self._recover_library_surface_after_backend_presence")
    binding_index = operation.index("visible_ui_binding = self._validate_exact_library_ui_binding")
    boundary_index = operation.index("soft_delete_boundary = self._fetch_xhr_protocol_sequence_boundary")
    assert initial_wait_index < recovery_index < binding_index < boundary_index
    assert "library_surface_not_authoritative_after_bounded_recovery" in operation
    assert "visible_library_ui_recovery" in operation
