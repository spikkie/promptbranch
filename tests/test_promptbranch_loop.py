from pathlib import Path
import json

from promptbranch_loop import (
    build_loop_action_walkthrough_payload,
    build_loop_read_only_evidence_gate,
    build_loop_read_only_evidence_report,
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


def test_loop_read_only_execution_inspects_paths_and_commands_without_execution():
    plan = plan_loop_target_file("examples/loop-targets/static-game-dry-run-target.json", execute_stubbed=True)
    from promptbranch_loop import build_loop_read_only_execution_payload

    payload = build_loop_read_only_execution_payload(plan, repo_root=Path.cwd())

    assert payload["ok"] is True
    assert payload["schema"] == "promptbranch.loop.read_only_execution"
    assert payload["mode"] == "read_only_execution"
    assert payload["execution_mode"] == "local_read_only_preflight"
    assert payload["executed_state"] == "REQUIREMENTS_CHECK"
    assert payload["summary"]["commands_executed"] == 0
    assert payload["side_effects_performed"] is False
    assert payload["safety"]["commands_executed"] is False
    assert payload["safety"]["project_source_mutation_performed"] is False
    assert payload["safety"]["artifact_adoption_performed"] is False
    assert payload["checks"]["allowed_paths"]
    assert all(item["repo_relative"] for item in payload["checks"]["allowed_paths"])
    assert all(item["execution_status"] == "not_executed_read_only" for item in payload["checks"]["validation_commands"])


def test_loop_read_only_execution_rejects_unsafe_paths(tmp_path: Path):
    target = tmp_path / "unsafe.json"
    target.write_text(
        json.dumps(
            {
                "schema": "promptbranch.loop.target",
                "schema_version": "1.0",
                "target_id": "unsafe-target",
                "goal": "Prove unsafe paths are rejected.",
                "allowed_paths": ["../outside"],
                "validation": {"commands": ["pytest -q"]},
                "human_required_when": ["unsafe path"],
            }
        ),
        encoding="utf-8",
    )
    plan = plan_loop_target_file(target, execute_stubbed=True)
    from promptbranch_loop import build_loop_read_only_execution_payload

    payload = build_loop_read_only_execution_payload(plan, repo_root=Path.cwd())

    assert payload["ok"] is False
    assert payload["status"] == "unsafe_path_scope"
    assert payload["summary"]["unsafe_path_count"] == 1
    assert payload["checks"]["allowed_paths"][0]["parent_traversal"] is True
    assert payload["side_effects_performed"] is False


def test_loop_read_only_execution_embeds_evidence_report():
    plan = plan_loop_target_file("examples/loop-targets/static-game-dry-run-target.json", execute_stubbed=True)
    from promptbranch_loop import build_loop_read_only_execution_payload

    payload = build_loop_read_only_execution_payload(plan, repo_root=Path.cwd())
    report = payload["evidence_report"]

    assert report["ok"] is True
    assert report["schema"] == "promptbranch.loop.read_only_evidence_report"
    assert report["source_schema"] == "promptbranch.loop.read_only_execution"
    assert report["evidence_summary"]["commands_executed"] == 0
    assert report["evidence_summary"]["unsafe_path_count"] == 0
    assert report["evidence_summary"]["declared_command_count"] == len(payload["checks"]["validation_commands"])
    assert all(item["executed"] is False for item in report["command_evidence"])
    assert report["safety_assertions"] == {
        "commands_executed": False,
        "files_mutated": False,
        "deployment_performed": False,
        "kubernetes_mutation_performed": False,
        "project_source_mutation_performed": False,
        "artifact_adoption_performed": False,
        "chatgpt_project_deletion_performed": False,
    }


def test_loop_read_only_evidence_report_blocks_unsafe_path():
    plan = plan_loop_target_file("examples/loop-targets/static-game-dry-run-target.json", execute_stubbed=True)
    from promptbranch_loop import build_loop_read_only_execution_payload

    payload = build_loop_read_only_execution_payload({**plan, "allowed_paths": ["../outside"]}, repo_root=Path.cwd())
    report = build_loop_read_only_evidence_report(payload)

    assert report["ok"] is False
    assert report["status"] == "evidence_blocked"
    assert report["blocked_reasons"] == ["unsafe_path_scope"]
    assert report["evidence_summary"]["unsafe_path_count"] == 1
    assert report["safety_assertions"]["commands_executed"] is False



def test_loop_read_only_evidence_gate_passes_clean_report():
    plan = plan_loop_target_file("examples/loop-targets/static-game-dry-run-target.json", execute_stubbed=True)
    from promptbranch_loop import build_loop_read_only_execution_payload

    payload = build_loop_read_only_execution_payload(plan, repo_root=Path.cwd())
    gate = build_loop_read_only_evidence_gate(payload["evidence_report"])

    assert gate["ok"] is True
    assert gate["schema"] == "promptbranch.loop.read_only_evidence_gate"
    assert gate["status"] == "gate_passed"
    assert gate["decision"] == "continue_to_next_dry_run_step"
    assert gate["gate_summary"]["failed_gate_count"] == 0
    assert gate["gate_summary"]["commands_executed"] == 0
    assert all(item["passed"] for item in gate["gates"])
    assert gate["side_effects_performed"] is False


def test_loop_read_only_evidence_gate_blocks_unsafe_report():
    plan = plan_loop_target_file("examples/loop-targets/static-game-dry-run-target.json", execute_stubbed=True)
    from promptbranch_loop import build_loop_read_only_execution_payload

    payload = build_loop_read_only_execution_payload({**plan, "allowed_paths": ["../outside"]}, repo_root=Path.cwd())
    report = build_loop_read_only_evidence_report(payload)
    gate = build_loop_read_only_evidence_gate(report)

    assert gate["ok"] is False
    assert gate["status"] == "gate_blocked"
    assert gate["decision"] == "stop_for_operator_review"
    assert "evidence_report_ok" in gate["blocked_reasons"]
    assert "no_unsafe_paths" in gate["blocked_reasons"]
    assert gate["gate_summary"]["unsafe_path_count"] == 1
    assert gate["safety_assertions"]["commands_executed"] is False


def test_loop_read_only_command_execution_runs_allowlisted_json_tool_without_mutation():
    from promptbranch_loop import build_loop_read_only_command_execution_payload, build_loop_read_only_execution_payload

    plan = plan_loop_target_file("examples/loop-targets/read-only-validation-command-target.json", execute_stubbed=True)
    read_only = build_loop_read_only_execution_payload(plan, repo_root=Path.cwd())
    gate = build_loop_read_only_evidence_gate(read_only["evidence_report"])
    payload = build_loop_read_only_command_execution_payload(read_only, gate, repo_root=Path.cwd())

    assert payload["ok"] is True
    assert payload["schema"] == "promptbranch.loop.read_only_command_execution"
    assert payload["status"] == "read_only_validation_executed"
    assert payload["summary"]["commands_executed"] == 1
    assert payload["summary"]["passed_command_count"] == 1
    assert payload["summary"]["mutation_detected"] is False
    assert payload["side_effects_performed"] is False
    command = payload["command_evidence"][0]
    assert command["execution_status"] == "executed_read_only_validation_passed"
    assert command["exit_code"] == 0
    assert command["before"] == command["after"]
    assert payload["safety"]["project_source_mutation_performed"] is False
    assert payload["safety"]["artifact_adoption_performed"] is False


def test_loop_read_only_command_execution_blocks_non_allowlisted_command(tmp_path: Path):
    from promptbranch_loop import build_loop_read_only_command_execution_payload, build_loop_read_only_execution_payload

    target = tmp_path / "unsafe-command.json"
    target.write_text(
        json.dumps(
            {
                "schema": "promptbranch.loop.target",
                "schema_version": "1.0",
                "target_id": "unsafe-command",
                "goal": "Block broad shell commands.",
                "allowed_paths": ["examples/loop-targets/read-only-validation-command-target.json"],
                "validation": {"commands": ["pytest -q tests/test_promptbranch_loop.py"]},
                "human_required_when": ["command_not_allowlisted"],
                "deployment": {"requested": False, "allowed": False},
                "max_iterations": 1,
            }
        ),
        encoding="utf-8",
    )
    plan = plan_loop_target_file(target, execute_stubbed=True)
    read_only = build_loop_read_only_execution_payload(plan, repo_root=Path.cwd())
    gate = build_loop_read_only_evidence_gate(read_only["evidence_report"])
    payload = build_loop_read_only_command_execution_payload(read_only, gate, repo_root=Path.cwd())

    assert payload["ok"] is False
    assert payload["summary"]["commands_executed"] == 0
    assert payload["summary"]["blocked_command_count"] == 1
    assert "blocked_not_allowlisted" in payload["blocked_reasons"]
    assert payload["command_evidence"][0]["executed"] is False
    assert payload["side_effects_performed"] is False


def test_loop_read_only_command_execution_blocks_json_tool_outside_allowed_paths(tmp_path: Path):
    from promptbranch_loop import build_loop_read_only_command_execution_payload, build_loop_read_only_execution_payload

    target = tmp_path / "outside-allowed.json"
    target.write_text(
        json.dumps(
            {
                "schema": "promptbranch.loop.target",
                "schema_version": "1.0",
                "target_id": "outside-allowed",
                "goal": "Block JSON tool against a path not covered by allowed_paths.",
                "allowed_paths": ["examples/k8s-game/**"],
                "validation": {"commands": ["python3 -m json.tool examples/loop-targets/read-only-validation-command-target.json"]},
                "human_required_when": ["outside_allowed_paths"],
                "deployment": {"requested": False, "allowed": False},
                "max_iterations": 1,
            }
        ),
        encoding="utf-8",
    )
    plan = plan_loop_target_file(target, execute_stubbed=True)
    read_only = build_loop_read_only_execution_payload(plan, repo_root=Path.cwd())
    gate = build_loop_read_only_evidence_gate(read_only["evidence_report"])
    payload = build_loop_read_only_command_execution_payload(read_only, gate, repo_root=Path.cwd())

    assert payload["ok"] is False
    assert payload["summary"]["commands_executed"] == 0
    assert "blocked_outside_allowed_paths" in payload["blocked_reasons"]
    assert payload["command_evidence"][0]["executed"] is False
