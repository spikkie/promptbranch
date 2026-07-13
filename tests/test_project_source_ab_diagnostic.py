from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from promptbranch_container_api import (
    _diagnostic_classify_legacy_reupload,
    _diagnostic_source_identity,
    _diagnostic_upload_identity,
    app,
)


def _upload_result(
    filename: str,
    *,
    file_id: str,
    libfile: str,
    committed: bool = True,
    ok: bool = True,
) -> dict:
    return {
        "ok": ok,
        "persistence_verified": bool(ok and committed),
        "save_request_summary": {
            "saw_commit": committed,
            "response_diagnostics": [
                {
                    "body_sample": (
                        '{"file_id":"%s","event":"file.indexing.completed",'
                        '"extra":{"metadata_object_id":"%s",'
                        '"library_file_name":"%s","mime_type":"text/plain"}}\n'
                        '{"file_id":"%s","event":"file.processing.completed",'
                        '"extra":null}\n'
                    )
                    % (file_id, libfile, filename, file_id),
                }
            ],
            "backing_file_ids": [file_id],
        },
    }


def _list_result(filename: str | None) -> dict:
    if filename is None:
        return {"ok": True, "count": 0, "sources": []}
    return {
        "ok": True,
        "count": 1,
        "sources": [
            {
                "name": filename,
                "title": filename,
                "identity": f"{filename} Document",
                "text": f"{filename} Document · Jul 13, 2026",
            }
        ],
    }


def test_upload_identity_reads_indexing_metadata_before_completed_event() -> None:
    result = _upload_result(
        "demo(1).txt",
        file_id="file_00000000000000000000000000000001",
        libfile="libfile_00000000000000000000000000000001",
    )
    identity = _diagnostic_upload_identity(result, "demo.txt")
    assert identity["requested_filename"] == "demo.txt"
    assert identity["library_assigned_filename"] == "demo(1).txt"
    assert identity["processed_file_id"].startswith("file_")
    assert identity["library_metadata_object_id"].startswith("libfile_")
    assert identity["completed_upload_event"]["event"] == "file.processing.completed"


def test_source_identity_reads_sources_array() -> None:
    identity = _diagnostic_source_identity(_list_result("demo.txt"), "demo.txt")
    assert identity["matching_identities"] == ["demo.txt Document"]
    assert identity["all_source_identities"] == ["demo.txt Document"]
    assert identity["exact_source_count"] == 1
    assert identity["suffix_source_count"] == 0
    assert identity["exact_source_name"] == "demo.txt"
    assert identity["exact_source_identity"] == "demo.txt Document"


def test_legacy_classifier_requires_new_file_and_libfile_ids() -> None:
    filename = "demo.txt"
    presence = {"ok": True, "source_identity": _diagnostic_source_identity(_list_result(filename), filename)}
    absence = {"ok": True, "source_identity": _diagnostic_source_identity(_list_result(None), filename)}
    first = _diagnostic_upload_identity(
        _upload_result(filename, file_id="file_same", libfile="libfile_same"), filename
    )
    second_result = _upload_result(filename, file_id="file_same", libfile="libfile_new")
    second = _diagnostic_upload_identity(second_result, filename)
    assert _diagnostic_classify_legacy_reupload(
        requested_filename=filename,
        first_presence=presence,
        remove_result={"ok": True},
        absence_result=absence,
        first_upload_identity=first,
        second_upload_result=second_result,
        second_upload_identity=second,
        final_presence=presence,
    ) == "second_upload_not_committed"


def test_legacy_classifier_detects_backend_suffix_after_verified_remove() -> None:
    filename = "demo.txt"
    presence = {"ok": True, "source_identity": _diagnostic_source_identity(_list_result(filename), filename)}
    absence = {"ok": True, "source_identity": _diagnostic_source_identity(_list_result(None), filename)}
    first = _diagnostic_upload_identity(
        _upload_result(filename, file_id="file_first", libfile="libfile_first"), filename
    )
    second_result = _upload_result("demo(1).txt", file_id="file_second", libfile="libfile_second", ok=False)
    second = _diagnostic_upload_identity(second_result, filename)
    assert _diagnostic_classify_legacy_reupload(
        requested_filename=filename,
        first_presence=presence,
        remove_result={"ok": True},
        absence_result=absence,
        first_upload_identity=first,
        second_upload_result=second_result,
        second_upload_identity=second,
        final_presence={"ok": False},
    ) == "backend_suffix_after_verified_remove"



def test_legacy_classifier_reports_remove_failed() -> None:
    filename = "demo.txt"
    presence = {"ok": True, "source_identity": _diagnostic_source_identity(_list_result(filename), filename)}
    absence = {"ok": False, "source_identity": _diagnostic_source_identity(_list_result(filename), filename)}
    first = _diagnostic_upload_identity(
        _upload_result(filename, file_id="file_first", libfile="libfile_first"), filename
    )
    assert _diagnostic_classify_legacy_reupload(
        requested_filename=filename,
        first_presence=presence,
        remove_result={"ok": False},
        absence_result=absence,
        first_upload_identity=first,
        second_upload_result={},
        second_upload_identity={},
        final_presence={"ok": False},
    ) == "remove_failed"


def test_legacy_classifier_reports_diagnostic_inconclusive_when_first_source_is_not_authoritative() -> None:
    filename = "demo.txt"
    first = _diagnostic_upload_identity(
        _upload_result(filename, file_id="file_first", libfile="libfile_first"), filename
    )
    assert _diagnostic_classify_legacy_reupload(
        requested_filename=filename,
        first_presence={"ok": False},
        remove_result={"ok": False},
        absence_result={"ok": False},
        first_upload_identity=first,
        second_upload_result={},
        second_upload_identity={},
        final_presence={"ok": False},
    ) == "diagnostic_inconclusive"

def test_project_source_ab_endpoint_executes_verified_legacy_remove_then_fresh_upload(monkeypatch) -> None:
    class RootService:
        async def create_project(self, *, name: str, memory_mode: str, keep_open: bool):
            assert memory_mode == "project-only"
            assert keep_open is False
            return {"ok": True, "project_name": name, "project_url": f"https://chatgpt.com/g/{name}/project"}

    class ProjectService:
        def __init__(self, project_url: str):
            self.project_url = project_url
            self.mode = "legacy" if "-legacy-" in project_url else "current"
            self.filename: str | None = None
            self.add_count = 0
            self.remove_calls: list[dict] = []

        async def add_project_source_diagnostic(self, **kwargs):
            assert Path(kwargs["file_path"]).exists()
            filename = kwargs["display_name"]
            self.add_count += 1
            if self.mode == "legacy":
                assert kwargs["transaction_mode"] == "legacy_10_75"
                assert kwargs["overwrite_existing"] is False
                self.filename = filename
                return _upload_result(
                    filename,
                    file_id=f"file_legacy_{self.add_count}",
                    libfile=f"libfile_legacy_{self.add_count}",
                )
            if self.add_count == 1:
                assert kwargs["overwrite_existing"] is False
                self.filename = filename
                return _upload_result(filename, file_id="file_current_1", libfile="libfile_current_1")
            assert kwargs["transaction_mode"] == "current"
            assert kwargs["overwrite_existing"] is True
            return {
                "ok": False,
                "status": "project_source_replace_not_supported",
                "persistence_verified": False,
                "save_request_summary": {"saw_commit": False, "response_diagnostics": []},
            }

        async def list_project_sources(self, *, keep_open: bool = False):
            assert keep_open is False
            return _list_result(self.filename)

        async def remove_project_source(self, **kwargs):
            assert self.mode == "legacy"
            assert kwargs["source_name"] == self.filename
            assert kwargs["exact"] is True
            self.remove_calls.append(dict(kwargs))
            removed = self.filename
            self.filename = None
            return {
                "ok": True,
                "action": "remove",
                "source_name": removed,
                "source_match": f"{removed} Document",
                "removed_via_ui": True,
            }

    root = RootService()
    services: dict[str, ProjectService] = {}

    def fake_service_for(project_url):
        if project_url is None:
            return root
        return services.setdefault(project_url, ProjectService(project_url))

    async def fake_preflight(project_url, *, allow_project_source_mutation: bool):
        assert project_url is None
        assert allow_project_source_mutation is True
        return {"auth_readiness": {"ok": True}, "runtime": {"ok": True}}

    async def no_sleep(_seconds: float):
        return None

    monkeypatch.setattr("promptbranch_container_api._service_for", fake_service_for)
    monkeypatch.setattr("promptbranch_container_api._require_project_source_mutation_preflight", fake_preflight)
    monkeypatch.setattr("promptbranch_container_api.asyncio.sleep", no_sleep)

    response = TestClient(app).post(
        "/v1/diagnostics/project-source-ab",
        json={"allow_project_source_mutation": True, "project_name_prefix": "itest-ab"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "diagnostic_completed"
    assert payload["conclusion"] == "canonical_reupload_succeeded"
    assert payload["legacy_transaction_classification"] == "canonical_reupload_succeeded"
    assert payload["current_transaction_classification"] == "current_transaction_failed"

    legacy = payload["transactions"]["legacy_10_75_transaction"]
    assert legacy["captured_source_name"] == legacy["requested_filename"]
    assert legacy["captured_source_identity"].endswith(" Document")
    assert legacy["remove_response"]["ok"] is True
    assert legacy["source_absence_after_remove"]["ok"] is True
    assert legacy["first_upload"]["processed_file_id"] != legacy["second_upload"]["processed_file_id"]
    assert legacy["first_upload"]["library_metadata_object_id"] != legacy["second_upload"]["library_metadata_object_id"]
    assert legacy["second_upload"]["upload_response"]["save_request_summary"]["saw_commit"] is True
    assert legacy["project_source_identity"]["matching_identities"]
    assert legacy["canonical_second_upload_success"] is True
    assert len(next(service for service in services.values() if service.mode == "legacy").remove_calls) == 1

    current = payload["transactions"]["current_transaction"]
    assert current["classification"] == "current_transaction_failed"
    assert current["canonical_second_upload_success"] is False
    assert payload["safety"]["release_artifact_uploaded"] is False
    assert payload["safety"]["adoption_attempted"] is False
