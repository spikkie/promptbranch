from __future__ import annotations
from pathlib import Path
from fastapi.testclient import TestClient
from promptbranch_container_api import (
    _diagnostic_classify_backing_reupload,
    _diagnostic_source_identity,
    _diagnostic_upload_identity,
    app,
)


def upload_result(filename: str, file_id: str, libfile: str, *, committed: bool = True) -> dict:
    body = (
        '{"file_id":"%s","event":"file.indexing.completed","extra":'
        '{"metadata_object_id":"%s","library_file_name":"%s","mime_type":"text/plain"}}\n'
        '{"file_id":"%s","event":"file.processing.completed","extra":null}\n'
    ) % (file_id, libfile, filename, file_id)
    return {
        "ok": committed,
        "persistence_verified": committed,
        "save_request_summary": {"saw_commit": committed, "response_diagnostics": [{"body_sample": body}]},
    }


def list_result(filename: str | None) -> dict:
    if not filename:
        return {"ok": True, "count": 0, "empty_state_visible": True, "sources": []}
    return {"ok": True, "count": 1, "empty_state_visible": False, "sources": [{
        "name": filename, "title": filename, "subtitle": "Document", "identity": f"{filename} Document", "text": f"{filename} Document"
    }]}


def test_backing_classifier_canonical_after_verified_delete() -> None:
    filename = "demo.txt"
    presence = {"ok": True, "source_identity": _diagnostic_source_identity(list_result(filename), filename)}
    absence = {"ok": True, "source_identity": _diagnostic_source_identity(list_result(None), filename)}
    first = _diagnostic_upload_identity(upload_result(filename, "file_first", "libfile_first"), filename)
    second_result = upload_result(filename, "file_second", "libfile_second")
    second = _diagnostic_upload_identity(second_result, filename)
    assert _diagnostic_classify_backing_reupload(
        requested_filename=filename,
        first_presence=presence,
        remove_result={"ok": True},
        absence_result=absence,
        delete_result={"ok": True, "exact_object_absent_verified": True},
        first_upload_identity=first,
        second_upload_result=second_result,
        second_upload_identity=second,
        final_presence=presence,
    ) == "canonical_reupload_after_backing_delete"


def test_backing_classifier_suffix_after_verified_delete() -> None:
    filename = "demo.txt"
    presence = {"ok": True, "source_identity": _diagnostic_source_identity(list_result(filename), filename)}
    absence = {"ok": True, "source_identity": _diagnostic_source_identity(list_result(None), filename)}
    first = _diagnostic_upload_identity(upload_result(filename, "file_first", "libfile_first"), filename)
    second_result = upload_result("demo(1).txt", "file_second", "libfile_second")
    second = _diagnostic_upload_identity(second_result, filename)
    assert _diagnostic_classify_backing_reupload(
        requested_filename=filename,
        first_presence=presence,
        remove_result={"ok": True},
        absence_result=absence,
        delete_result={"ok": True, "exact_object_absent_verified": True},
        first_upload_identity=first,
        second_upload_result=second_result,
        second_upload_identity=second,
        final_presence={"ok": False},
    ) == "backend_suffix_after_verified_backing_delete"


def test_backing_classifier_delete_not_supported() -> None:
    filename = "demo.txt"
    presence = {"ok": True}
    absence = {"ok": True}
    assert _diagnostic_classify_backing_reupload(
        requested_filename=filename,
        first_presence=presence,
        remove_result={"ok": True},
        absence_result=absence,
        delete_result={"ok": False, "status": "exact_library_backing_delete_not_supported"},
        first_upload_identity={}, second_upload_result={}, second_upload_identity={}, final_presence={},
    ) == "backing_library_delete_not_supported"


def test_endpoint_deletes_known_target_and_new_backing_before_canonical_reupload(monkeypatch) -> None:
    class RootService:
        def __init__(self):
            self.delete_calls = []
        async def create_project(self, *, name: str, memory_mode: str, keep_open: bool):
            return {"ok": True, "project_name": name, "project_url": f"https://chatgpt.com/g/{name}/project"}
        async def delete_library_backing_object_diagnostic(self, **kwargs):
            self.delete_calls.append(dict(kwargs))
            return {"ok": True, "status": "exact_library_backing_object_deleted", "exact_object_absent_verified": True}

    class ProjectService:
        def __init__(self):
            self.filename = None
            self.add_count = 0
        async def add_project_source_diagnostic(self, **kwargs):
            assert kwargs["transaction_mode"] == "legacy_10_75"
            assert kwargs["overwrite_existing"] is False
            assert Path(kwargs["file_path"]).exists()
            self.add_count += 1
            self.filename = kwargs["display_name"]
            return upload_result(self.filename, f"file_new_{self.add_count}", f"libfile_new_{self.add_count}")
        async def list_project_sources(self, *, keep_open: bool = False):
            return list_result(self.filename)
        async def remove_project_source(self, **kwargs):
            removed = self.filename
            self.filename = None
            return {"ok": True, "action": "remove", "source_name": removed, "removed_via_ui": True}

    root = RootService()
    project = ProjectService()
    def fake_service_for(project_url):
        return root if project_url is None else project
    async def fake_preflight(project_url, *, allow_project_source_mutation: bool):
        return {"auth_readiness": {"ok": True}, "runtime": {"ok": True}}
    async def no_sleep(_seconds: float):
        return None
    monkeypatch.setattr("promptbranch_container_api._service_for", fake_service_for)
    monkeypatch.setattr("promptbranch_container_api._require_project_source_mutation_preflight", fake_preflight)
    monkeypatch.setattr("promptbranch_container_api.asyncio.sleep", no_sleep)

    response = TestClient(app).post("/v1/diagnostics/library-backing-reupload", json={
        "allow_project_source_mutation": True,
        "initial_target_processed_file_id": "file_00000000a7cc71f48c35989259e6dc33",
        "initial_target_library_metadata_object_id": "libfile_8b26b82651e88191a9e965b267290f5b",
        "initial_target_filename": "pb-ab-legacy-28f3d84be7.txt",
    })
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["conclusion"] == "canonical_reupload_after_backing_delete"
    assert payload["known_target_cleanup"]["ok"] is True
    assert payload["backing_library_delete"]["exact_object_absent_verified"] is True
    assert payload["first_upload"]["processed_file_id"] != payload["second_upload"]["processed_file_id"]
    assert payload["first_upload"]["library_metadata_object_id"] != payload["second_upload"]["library_metadata_object_id"]
    assert len(root.delete_calls) == 2
    assert root.delete_calls[0]["processed_file_id"] == "file_00000000a7cc71f48c35989259e6dc33"
    assert payload["safety"]["previous_suffix_evidence_source_touched"] is False
