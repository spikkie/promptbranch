from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from fastapi.testclient import TestClient

from promptbranch_container_api import _diagnostic_upload_identity, app


def _upload_result(filename: str, *, second: bool = False) -> dict:
    file_id = "file_00000000000000000000000000000001"
    libfile = "libfile_00000000000000000000000000000001"
    result = {
        "ok": True,
        "persistence_verified": True,
        "save_request_summary": {
            "response_diagnostics": [
                {
                    "body_sample": (
                        '{"file_id":"%s","event":"file.processing.completed",'
                        '"extra":{"metadata_object_id":"%s",'
                        '"library_file_name":"%s","mime_type":"text/plain"}}\n'
                    )
                    % (file_id, libfile, filename),
                }
            ],
            "backing_file_ids": [file_id],
        },
    }
    if second:
        result["overwrite_remove_result"] = {
            "ok": True,
            "action": "remove",
            "source_name": filename,
            "removed_via_ui": True,
        }
    return result


def test_upload_identity_prefers_completed_library_metadata() -> None:
    result = _upload_result("demo(1).txt")
    identity = _diagnostic_upload_identity(result, "demo.txt")
    assert identity["requested_filename"] == "demo.txt"
    assert identity["library_assigned_filename"] == "demo(1).txt"
    assert identity["processed_file_id"].startswith("file_")
    assert identity["library_metadata_object_id"].startswith("libfile_")


def test_project_source_ab_endpoint_runs_both_modes_without_release_or_adoption(monkeypatch) -> None:
    calls: dict[str, int] = defaultdict(int)
    filenames: dict[str, str] = {}

    class RootService:
        async def create_project(self, *, name: str, memory_mode: str, keep_open: bool):
            assert memory_mode == "project-only"
            assert keep_open is False
            return {"ok": True, "project_name": name, "project_url": f"https://chatgpt.com/g/{name}/project"}

    class ProjectService:
        def __init__(self, project_url: str):
            self.project_url = project_url

        async def add_project_source_diagnostic(self, **kwargs):
            mode = kwargs["transaction_mode"]
            assert mode in {"legacy_10_75", "current"}
            assert Path(kwargs["file_path"]).exists()
            filename = kwargs["display_name"]
            filenames[self.project_url] = filename
            calls[self.project_url] += 1
            return _upload_result(filename, second=calls[self.project_url] == 2)

        async def list_project_sources(self, *, keep_open: bool = False):
            assert keep_open is False
            return {"ok": True, "count": 1, "source_identities": [f"{filenames[self.project_url]} Document"]}

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

    monkeypatch.setattr("promptbranch_container_api._service_for", fake_service_for)
    monkeypatch.setattr("promptbranch_container_api._require_project_source_mutation_preflight", fake_preflight)

    response = TestClient(app).post(
        "/v1/diagnostics/project-source-ab",
        json={"allow_project_source_mutation": True, "project_name_prefix": "itest-ab"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "diagnostic_completed"
    assert payload["conclusion"] == "both_transactions_work"
    assert set(payload["transactions"]) == {"legacy_10_75_transaction", "current_transaction"}
    assert payload["transactions"]["legacy_10_75_transaction"]["transaction_mode"] == "legacy_10_75"
    assert payload["transactions"]["current_transaction"]["transaction_mode"] == "current"
    assert payload["safety"]["release_artifact_uploaded"] is False
    assert payload["safety"]["adoption_attempted"] is False
    assert payload["safety"]["platform_gitops_file_used"] is False
    assert all(count == 2 for count in calls.values())
