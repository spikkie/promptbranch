import json
from pathlib import Path

from promptbranch_loop import (
    build_loop_action_walkthrough_payload,
    build_loop_read_only_execution_payload,
    build_loop_state_only_payload,
    plan_loop_target_file,
    validate_loop_target_file,
)


def test_loop_target_schema_validates_static_game_fixture():
    payload = validate_loop_target_file("examples/loop-targets/static-game-dry-run-target.json")
    assert payload["ok"] is True
    assert payload["status"] == "target_valid"
    assert payload["schema"] == "promptbranch.loop.target"
    assert payload["schema_version"] == "1.0"
    assert payload["target_id"] == "k8s-game-static-dry-run"
    assert payload["side_effects_performed"] is False
    assert payload["deployment_allowed"] is False
    assert payload["artifact_adoption_allowed"] is False
    assert payload["project_source_mutation_allowed"] is False


def test_loop_plan_is_dry_run_only_and_reaches_solved():
    payload = plan_loop_target_file("examples/loop-targets/static-game-dry-run-target.json")
    assert payload["ok"] is True
    assert payload["action"] == "loop_plan"
    assert payload["status"] == "planned"
    assert payload["final_state"] == "SOLVED"
    assert payload["side_effects_performed"] is False
    assert payload["safety"] == {
        "side_effects_performed": False,
        "mutation_allowed": False,
        "commands_executed": False,
        "deployment_performed": False,
        "kubernetes_mutation_performed": False,
        "project_source_mutation_performed": False,
        "artifact_adoption_performed": False,
        "chatgpt_project_deletion_performed": False,
    }
    assert "DEPLOY_STUB" not in payload["planned_states"]
    assert payload["planned_states"][-1] == "SOLVED"


def test_loop_plan_classifies_missing_validation_requirements():
    payload = plan_loop_target_file("examples/loop-targets/missing-requirements-target.json")
    assert payload["ok"] is False
    assert payload["status"] == "requirements_missing"
    assert payload["final_state"] == "REQUIREMENTS_MISSING"
    assert payload["side_effects_performed"] is False
    assert payload["planned_states"] == ["INTAKE", "REQUIREMENTS_CHECK", "REQUIREMENTS_MISSING"]


def test_loop_invalid_target_does_not_perform_side_effects(tmp_path: Path):
    target = tmp_path / "invalid.json"
    target.write_text('{"schema":"promptbranch.loop.target","schema_version":"1.0","goal":"missing target id"}\n', encoding="utf-8")
    payload = plan_loop_target_file(target)
    assert payload["ok"] is False
    assert payload["status"] == "invalid_target"
    assert payload["final_state"] == "BLOCKED"
    assert payload["side_effects_performed"] is False
    assert payload["safety"]["deployment_performed"] is False


def test_loop_state_only_payload_is_presentation_only():
    plan = plan_loop_target_file("examples/loop-targets/static-game-dry-run-target.json", execute_stubbed=True)
    payload = build_loop_state_only_payload(plan)
    assert payload["ok"] is True
    assert payload["mode"] == "state_only"
    assert payload["states"] == plan["planned_states"]
    assert payload["state_count"] == len(plan["planned_states"])
    assert payload["side_effects_performed"] is False
    assert payload["safety"]["commands_executed"] is False
    assert payload["safety"]["deployment_performed"] is False
    assert payload["safety"]["project_source_mutation_performed"] is False
    assert payload["safety"]["artifact_adoption_performed"] is False
    assert "events" not in payload


def test_loop_action_walkthrough_payload_is_dry_run_only():
    plan = plan_loop_target_file("examples/loop-targets/static-game-dry-run-target.json", execute_stubbed=True)
    payload = build_loop_action_walkthrough_payload(plan)
    assert payload["ok"] is True
    assert payload["schema"] == "promptbranch.loop.action_walkthrough"
    assert payload["mode"] == "planned_actions"
    assert payload["states"] == plan["planned_states"]
    assert payload["action_count"] == len(plan["planned_states"])
    assert payload["side_effects_performed"] is False
    assert payload["safety"]["commands_executed"] is False
    assert payload["safety"]["deployment_performed"] is False
    assert payload["safety"]["project_source_mutation_performed"] is False
    assert payload["safety"]["artifact_adoption_performed"] is False
    assert "events" not in payload
    first = payload["actions"][0]
    assert first["state"] == "INTAKE"
    assert first["planned_action"] == "load target definition and create loop context"
    assert first["validation_gate"] == "target JSON parsed and target_id/goal are available"
    assert first["execution_status"] == "not_executed_dry_run"


def test_loop_read_only_execution_payload_inspects_target_without_mutation():
    plan = plan_loop_target_file("examples/loop-targets/static-game-dry-run-target.json", execute_stubbed=True)
    payload = build_loop_read_only_execution_payload(plan)
    assert payload["ok"] is True
    assert payload["schema"] == "promptbranch.loop.read_only_execution"
    assert payload["mode"] == "read_only_execution"
    assert payload["execution_mode"] == "local_read_only_preflight"
    assert payload["executed_state"] == "REQUIREMENTS_CHECK"
    assert payload["read_operations_performed"] is True
    assert payload["side_effects_performed"] is False
    assert payload["safety"]["commands_executed"] is False
    assert payload["safety"]["deployment_performed"] is False
    assert payload["safety"]["kubernetes_mutation_performed"] is False
    assert payload["safety"]["project_source_mutation_performed"] is False
    assert payload["safety"]["artifact_adoption_performed"] is False
    assert payload["summary"]["allowed_path_count"] == 3
    assert payload["summary"]["validation_command_count"] == 2
    assert payload["summary"]["commands_executed"] == 0
    assert all(item["safe"] for item in payload["checks"]["allowed_paths"])
    assert all(item["execution_status"] == "not_executed_read_only" for item in payload["checks"]["validation_commands"])


def test_loop_read_only_execution_rejects_unsafe_allowed_path(tmp_path: Path):
    target = tmp_path / "unsafe.json"
    target.write_text(json.dumps({
        "schema": "promptbranch.loop.target",
        "schema_version": "1.0",
        "target_id": "unsafe-path-target",
        "goal": "Prove read-only checks reject path breakout.",
        "allowed_paths": ["../outside"],
        "validation": {"commands": ["pytest -q tests/test_dummy.py"]},
    }) + "\n", encoding="utf-8")
    plan = plan_loop_target_file(target, execute_stubbed=True)
    payload = build_loop_read_only_execution_payload(plan)
    assert payload["ok"] is False
    assert payload["status"] == "unsafe_path_scope"
    assert payload["summary"]["unsafe_path_count"] == 1
    assert payload["checks"]["allowed_paths"][0]["parent_traversal"] is True
    assert payload["side_effects_performed"] is False
