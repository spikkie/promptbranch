from __future__ import annotations

from pathlib import Path

from promptbranch_source_queue import (
    build_source_mutation_queue_plan,
    workspace_id_from_url,
)


def test_source_queue_plan_serializes_add_per_workspace() -> None:
    payload = build_source_mutation_queue_plan(
        operation="add",
        state_snapshot={"resolved_project_home_url": "https://chatgpt.com/g/g-p-demo/project"},
        file_path="demo.zip",
        display_name="demo.zip",
    )

    assert payload["ok"] is True
    assert payload["status"] == "planned"
    assert payload["planning_only"] is True
    assert payload["mutation_executed"] is False
    assert payload["scheduler_operation"] == "src_add"
    assert payload["queue_policy"]["per_workspace_source_mutations_serialized"] is True
    assert payload["workspace"]["lock_scope"] == "sources:g-p-demo"
    assert any(item["resource"] == "sources:g-p-demo:exclusive" for item in payload["resource_plan"]["resources"])
    assert payload["verification_plan"]["collateral_change_detection"] is True
    assert payload["verification_plan"]["state_update_before_verification_allowed"] is False


def test_source_queue_plan_requires_workspace_before_mutation() -> None:
    payload = build_source_mutation_queue_plan(operation="add", state_snapshot={}, file_path="demo.zip")

    assert payload["ok"] is False
    assert payload["status"] == "missing_context"
    assert "workspace_url" in payload["missing_context"]
    assert payload["mutation_executed"] is False


def test_source_queue_plan_handles_remove_as_exclusive_source_mutation() -> None:
    payload = build_source_mutation_queue_plan(
        operation="remove",
        workspace_url="https://chatgpt.com/g/g-p-demo/project",
        source_name="old.zip",
        exact=True,
    )

    assert payload["ok"] is True
    assert payload["scheduler_operation"] == "src_remove"
    assert payload["request"]["exact"] is True
    assert "pb src rm old.zip --exact --json" in payload["next_safe_commands"]


def test_workspace_id_from_url_is_stable_for_non_project_urls() -> None:
    first = workspace_id_from_url("https://example.com/workspace/a")
    second = workspace_id_from_url("https://example.com/workspace/a")

    assert first == second
    assert first and first.startswith("workspace-")


def test_source_queue_module_is_declared_for_setuptools_install() -> None:
    import tomllib

    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    modules = data["tool"]["setuptools"]["py-modules"]

    assert "promptbranch_source_queue" in modules
