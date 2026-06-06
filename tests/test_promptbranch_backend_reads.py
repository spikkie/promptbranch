from __future__ import annotations

import tomllib
from pathlib import Path

from promptbranch_backend_reads import (
    backend_reads_diagnostics,
    backend_reads_plan,
    classify_source_list_payload,
    classify_task_list_payload,
)


def test_backend_reads_plan_documents_task_and_source_precedence() -> None:
    payload = backend_reads_plan()

    assert payload["ok"] is True
    assert payload["schema"] == "promptbranch.backend_reads.plan"
    assert payload["runtime_integration"] == "read_only_diagnostic"
    assert payload["operations"]["task_list"]["source_of_truth_order"][0].startswith("backend JSON")
    assert payload["operations"]["source_list"]["mutation_allowed"] is False


def test_task_list_payload_classifies_backend_indexed_sources() -> None:
    payload = classify_task_list_payload({
        "count": 2,
        "indexed_task_count": 2,
        "recent_state_count": 0,
        "source_counts": {"snorlax": 2, "dom": 2},
    })

    assert payload["status"] == "backend_indexed"
    assert payload["backend_first_satisfied"] is True
    assert payload["backend_observation_count"] == 2
    assert payload["fallback_used"] is True


def test_task_list_payload_classifies_recent_state_only_as_not_backend_first() -> None:
    payload = classify_task_list_payload({
        "count": 1,
        "recent_state_count": 1,
        "source_counts": {"recent_state": 1},
    })

    assert payload["status"] == "fallback_only"
    assert payload["backend_first_satisfied"] is False
    assert payload["fallback_observation_count"] == 1


def test_source_list_payload_flags_metadata_gap_when_origin_is_absent() -> None:
    payload = classify_source_list_payload({
        "ok": True,
        "sources": [{"title": "demo.zip"}],
        "count": 1,
    })

    assert payload["status"] == "undifferentiated"
    assert payload["metadata_gap"] is True
    assert payload["backend_first_satisfied"] is False


def test_backend_reads_diagnostics_reports_metadata_gaps() -> None:
    payload = backend_reads_diagnostics(
        task_payload={"count": 1, "indexed_task_count": 1, "source_counts": {"project_endpoint": 1}},
        source_payload={"sources": [{"title": "demo.zip"}], "count": 1},
    )

    assert payload["ok"] is True
    assert payload["status"] == "metadata_gap"
    assert payload["diagnostic_count"] == 2
    assert payload["metadata_gaps"] == ["source_list"]


def test_backend_reads_module_is_declared_for_setuptools_install() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    modules = data["tool"]["setuptools"]["py-modules"]

    assert "promptbranch_backend_reads" in modules


def test_task_list_read_routing_prefers_backend_and_skips_history() -> None:
    from promptbranch_backend_reads import task_list_read_routing

    payload = task_list_read_routing(
        {"count": 2, "indexed_task_count": 2, "source_counts": {"project_endpoint": 2}},
        history_fallback_requested=True,
        history_fallback_used=False,
    )

    assert payload["mode"] == "backend_first"
    assert payload["selected_path"] == "backend_first"
    assert payload["backend_first_satisfied"] is True
    assert payload["history_fallback_requested"] is True
    assert payload["history_fallback_used"] is False


def test_source_list_read_routing_blocks_backend_first_on_metadata_gap() -> None:
    from promptbranch_backend_reads import source_list_read_routing

    payload = source_list_read_routing({"ok": True, "sources": [{"title": "demo.zip"}], "count": 1})

    assert payload["mode"] == "backend_first_blocked"
    assert payload["selected_path"] == "explicit_fallback_metadata_gap"
    assert payload["metadata_gap"] is True
    assert payload["backend_first_satisfied"] is False
