from __future__ import annotations

from pathlib import Path

from promptbranch_scheduler import conflict_matrix, plan_operation_resources, queue_list, queue_status


def test_queue_status_is_read_only_and_lists_known_operations(tmp_path: Path) -> None:
    payload = queue_status(repo_path=tmp_path)

    assert payload["ok"] is True
    assert payload["action"] == "queue_status"
    assert payload["schema"] == "promptbranch.scheduler.status"
    assert payload["runtime_integration"] == "inspection_only"
    assert payload["active_count"] == 0
    assert payload["queued_count"] == 0
    assert "src_add" in payload["known_operations"]
    assert not Path(payload["operation_log"]).exists()


def test_queue_list_returns_empty_operation_set_without_queue_log(tmp_path: Path) -> None:
    payload = queue_list(repo_path=tmp_path)

    assert payload["ok"] is True
    assert payload["action"] == "queue_list"
    assert payload["operation_count"] == 0
    assert payload["operations"] == []


def test_plan_operation_resources_renders_context_for_source_mutation() -> None:
    payload = plan_operation_resources(
        "src_add",
        {
            "account_id": "default",
            "project_id": "project-1",
            "service_id": "default",
        },
    )

    assert payload["ok"] is True
    assert payload["status"] == "planned"
    assert payload["operation"] == "src_add"
    assert payload["queue_required"] is True
    assert payload["transactional"] is True
    resources = {item["resource"] for item in payload["resources"]}
    assert "sources:project-1:exclusive" in resources
    assert "service_profile:default:exclusive" in resources


def test_plan_operation_reports_missing_context_without_guessing() -> None:
    payload = plan_operation_resources("src_add", {"account_id": "default"})

    assert payload["ok"] is False
    assert payload["status"] == "missing_context"
    assert payload["missing_context"] == ["project_id", "service_id"]
    assert any("{project_id}" in item["resource"] for item in payload["resources"])


def test_conflict_matrix_detects_same_workspace_source_mutation_conflict() -> None:
    payload = conflict_matrix(
        "src_add",
        "src_sync",
        {
            "account_id": "default",
            "project_id": "project-1",
            "service_id": "default",
            "repo_path": ".",
        },
    )

    assert payload["ok"] is True
    assert payload["status"] == "conflict"
    assert payload["conflict_count"] >= 1
    assert any(item["scope"] == "sources:project-1" for item in payload["conflicts"])


def test_conflict_matrix_allows_independent_stateless_reads() -> None:
    payload = conflict_matrix("version", "version", {})

    assert payload["ok"] is True
    assert payload["status"] == "compatible"
    assert payload["conflict_count"] == 0
