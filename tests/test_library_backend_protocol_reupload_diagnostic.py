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
    assert result["ok"] is True
    assert result["row_scoped_menu_binding"] is True
    assert clicked == [
        "row-menu:library-disposable-row-options",
        "delete-action:library-disposable-delete-action",
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
