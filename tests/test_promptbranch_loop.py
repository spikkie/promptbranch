from pathlib import Path

from promptbranch_loop import plan_loop_target_file, validate_loop_target_file


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
