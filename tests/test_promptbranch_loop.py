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


def test_loop_read_only_command_diagnosis_classifies_passed_result():
    from promptbranch_loop import (
        build_loop_read_only_command_diagnosis_payload,
        build_loop_read_only_command_execution_payload,
        build_loop_read_only_execution_payload,
    )

    plan = plan_loop_target_file("examples/loop-targets/read-only-validation-command-target.json", execute_stubbed=True)
    read_only = build_loop_read_only_execution_payload(plan, repo_root=Path.cwd())
    gate = build_loop_read_only_evidence_gate(read_only["evidence_report"])
    execution = build_loop_read_only_command_execution_payload(read_only, gate, repo_root=Path.cwd())
    diagnosis = build_loop_read_only_command_diagnosis_payload(execution)

    assert diagnosis["ok"] is True
    assert diagnosis["schema"] == "promptbranch.loop.read_only_command_diagnosis"
    assert diagnosis["status"] == "diagnosis_passed_result"
    assert diagnosis["result_classification"] == "passed"
    assert diagnosis["summary"]["passed_command_count"] == 1
    assert diagnosis["summary"]["correction_plan_generated"] is False
    assert diagnosis["summary"]["files_mutated"] is False
    assert diagnosis["safety"]["project_source_mutation_performed"] is False
    assert diagnosis["safety"]["artifact_adoption_performed"] is False


def test_loop_read_only_command_diagnosis_classifies_blocked_result(tmp_path: Path):
    from promptbranch_loop import (
        build_loop_read_only_command_diagnosis_payload,
        build_loop_read_only_command_execution_payload,
        build_loop_read_only_execution_payload,
    )

    target = tmp_path / "blocked-command.json"
    target.write_text(
        json.dumps(
            {
                "schema": "promptbranch.loop.target",
                "schema_version": "1.0",
                "target_id": "blocked-command",
                "goal": "Classify a non-allowlisted command as blocked without corrections.",
                "allowed_paths": ["sample.json"],
                "validation": {"commands": ["pytest -q tests/test_promptbranch_loop.py"]},
                "human_required_when": ["command_not_allowlisted"],
                "deployment": {"requested": False, "allowed": False},
                "max_iterations": 1,
            }
        ),
        encoding="utf-8",
    )
    plan = plan_loop_target_file(target, execute_stubbed=True)
    read_only = build_loop_read_only_execution_payload(plan, repo_root=tmp_path)
    gate = build_loop_read_only_evidence_gate(read_only["evidence_report"])
    execution = build_loop_read_only_command_execution_payload(read_only, gate, repo_root=tmp_path)
    diagnosis = build_loop_read_only_command_diagnosis_payload(execution)

    assert diagnosis["ok"] is True
    assert diagnosis["status"] == "diagnosis_blocked_result"
    assert diagnosis["result_classification"] == "blocked"
    assert diagnosis["summary"]["blocked_command_count"] == 1
    assert diagnosis["blocked_reasons"] == ["blocked_not_allowlisted"]
    assert diagnosis["diagnoses"][0]["correction_plan_generated"] is False
    assert diagnosis["side_effects_performed"] is False


def test_loop_read_only_command_diagnosis_classifies_failed_result(tmp_path: Path):
    from promptbranch_loop import (
        build_loop_read_only_command_diagnosis_payload,
        build_loop_read_only_command_execution_payload,
        build_loop_read_only_execution_payload,
    )

    (tmp_path / "bad.json").write_text("{not-json\n", encoding="utf-8")
    target = tmp_path / "failed-command.json"
    target.write_text(
        json.dumps(
            {
                "schema": "promptbranch.loop.target",
                "schema_version": "1.0",
                "target_id": "failed-command",
                "goal": "Classify a failed read-only JSON validation command without corrections.",
                "allowed_paths": ["bad.json"],
                "validation": {"commands": ["python3 -m json.tool bad.json"]},
                "human_required_when": ["validation_failed"],
                "deployment": {"requested": False, "allowed": False},
                "max_iterations": 1,
            }
        ),
        encoding="utf-8",
    )
    plan = plan_loop_target_file(target, execute_stubbed=True)
    read_only = build_loop_read_only_execution_payload(plan, repo_root=tmp_path)
    gate = build_loop_read_only_evidence_gate(read_only["evidence_report"])
    execution = build_loop_read_only_command_execution_payload(read_only, gate, repo_root=tmp_path)
    diagnosis = build_loop_read_only_command_diagnosis_payload(execution)

    assert execution["ok"] is False
    assert diagnosis["ok"] is True
    assert diagnosis["status"] == "diagnosis_failed_result"
    assert diagnosis["result_classification"] == "failed"
    assert diagnosis["summary"]["failed_command_count"] == 1
    assert diagnosis["failed_reasons"] == ["read_only_validation_command_failed"]
    assert diagnosis["correction_plan"] is None
    assert diagnosis["safety"]["files_mutated"] is False


def test_loop_read_only_correction_plan_generates_failed_result_plan_without_mutation(tmp_path: Path):
    from promptbranch_loop import (
        build_loop_read_only_command_diagnosis_payload,
        build_loop_read_only_command_execution_payload,
        build_loop_read_only_correction_plan_payload,
        build_loop_read_only_execution_payload,
    )

    (tmp_path / "bad.json").write_text("{not-json\n", encoding="utf-8")
    target = tmp_path / "failed-command.json"
    target.write_text(
        json.dumps(
            {
                "schema": "promptbranch.loop.target",
                "schema_version": "1.0",
                "target_id": "failed-command-plan",
                "goal": "Generate a non-mutating correction plan for a failed read-only command.",
                "allowed_paths": ["bad.json"],
                "validation": {"commands": ["python3 -m json.tool bad.json"]},
                "human_required_when": ["validation_failed"],
                "deployment": {"requested": False, "allowed": False},
                "max_iterations": 1,
            }
        ),
        encoding="utf-8",
    )
    plan = plan_loop_target_file(target, execute_stubbed=True)
    read_only = build_loop_read_only_execution_payload(plan, repo_root=tmp_path)
    gate = build_loop_read_only_evidence_gate(read_only["evidence_report"])
    execution = build_loop_read_only_command_execution_payload(read_only, gate, repo_root=tmp_path)
    diagnosis = build_loop_read_only_command_diagnosis_payload(execution)
    correction = build_loop_read_only_correction_plan_payload(diagnosis)

    assert correction["ok"] is True
    assert correction["schema"] == "promptbranch.loop.read_only_correction_plan"
    assert correction["status"] == "correction_plan_generated_failed_result"
    assert correction["source_result_classification"] == "failed"
    assert correction["summary"]["correction_plan_generated"] is True
    assert correction["summary"]["commands_executed"] == 0
    assert correction["summary"]["files_mutated"] is False
    assert correction["safety"]["correction_plan_only"] is True
    assert correction["safety"]["files_mutated"] is False
    assert correction["safety"]["project_source_mutation_performed"] is False
    assert correction["correction_plan"]["file_changes"] == []
    assert correction["correction_plan"]["write_actions"] == []
    assert correction["correction_plan"]["commands_to_execute_now"] == []
    assert correction["correction_plan"]["future_slice_required_for_file_mutation"] is True
    assert correction["correction_plan"]["entries"][0]["plan_type"] == "bounded_operator_correction_plan"


def test_loop_read_only_correction_plan_generates_blocked_result_plan_without_mutation(tmp_path: Path):
    from promptbranch_loop import (
        build_loop_read_only_command_diagnosis_payload,
        build_loop_read_only_command_execution_payload,
        build_loop_read_only_correction_plan_payload,
        build_loop_read_only_execution_payload,
    )

    target = tmp_path / "blocked-command.json"
    target.write_text(
        json.dumps(
            {
                "schema": "promptbranch.loop.target",
                "schema_version": "1.0",
                "target_id": "blocked-command-plan",
                "goal": "Generate a non-mutating correction plan for a blocked command.",
                "allowed_paths": ["sample.json"],
                "validation": {"commands": ["pytest -q tests/test_promptbranch_loop.py"]},
                "human_required_when": ["command_not_allowlisted"],
                "deployment": {"requested": False, "allowed": False},
                "max_iterations": 1,
            }
        ),
        encoding="utf-8",
    )
    plan = plan_loop_target_file(target, execute_stubbed=True)
    read_only = build_loop_read_only_execution_payload(plan, repo_root=tmp_path)
    gate = build_loop_read_only_evidence_gate(read_only["evidence_report"])
    execution = build_loop_read_only_command_execution_payload(read_only, gate, repo_root=tmp_path)
    diagnosis = build_loop_read_only_command_diagnosis_payload(execution)
    correction = build_loop_read_only_correction_plan_payload(diagnosis)

    assert correction["ok"] is True
    assert correction["status"] == "correction_plan_generated_blocked_result"
    assert correction["source_result_classification"] == "blocked"
    assert correction["summary"]["correction_required_count"] == 1
    assert correction["side_effects_performed"] is False
    entry = correction["correction_plan"]["entries"][0]
    assert entry["source_reason"] == "blocked_not_allowlisted"
    assert all(step["mutation_allowed"] is False for step in entry["steps"])


def test_loop_read_only_correction_plan_for_passed_result_requires_no_correction():
    from promptbranch_loop import (
        build_loop_read_only_command_diagnosis_payload,
        build_loop_read_only_command_execution_payload,
        build_loop_read_only_correction_plan_payload,
        build_loop_read_only_execution_payload,
    )

    plan = plan_loop_target_file("examples/loop-targets/read-only-validation-command-target.json", execute_stubbed=True)
    read_only = build_loop_read_only_execution_payload(plan, repo_root=Path.cwd())
    gate = build_loop_read_only_evidence_gate(read_only["evidence_report"])
    execution = build_loop_read_only_command_execution_payload(read_only, gate, repo_root=Path.cwd())
    diagnosis = build_loop_read_only_command_diagnosis_payload(execution)
    correction = build_loop_read_only_correction_plan_payload(diagnosis)

    assert correction["ok"] is True
    assert correction["status"] == "correction_plan_not_required"
    assert correction["source_result_classification"] == "passed"
    assert correction["summary"]["correction_plan_generated"] is False
    assert correction["summary"]["no_correction_required_count"] == 1
    assert correction["safety"]["files_mutated"] is False


def test_loop_sandbox_file_mutation_mutates_temp_fixture_only(tmp_path: Path):
    from promptbranch_loop import (
        build_loop_read_only_command_diagnosis_payload,
        build_loop_read_only_command_execution_payload,
        build_loop_read_only_correction_plan_payload,
        build_loop_read_only_execution_payload,
        build_loop_sandbox_file_mutation_payload,
    )

    fixture = tmp_path / "examples" / "loop-sandbox" / "invalid-json-fixture.json"
    fixture.parent.mkdir(parents=True)
    fixture.write_text('{"status": "broken",\n', encoding="utf-8")
    before_text = fixture.read_text(encoding="utf-8")
    target = tmp_path / "target.json"
    target.write_text(
        json.dumps(
            {
                "schema": "promptbranch.loop.target",
                "schema_version": "1.0",
                "target_id": "sandbox-mutation-test",
                "goal": "Mutate only a temporary sandbox copy.",
                "allowed_paths": ["examples/loop-sandbox/invalid-json-fixture.json"],
                "validation": {"commands": ["python3 -m json.tool examples/loop-sandbox/invalid-json-fixture.json"]},
                "sandbox_mutation": {
                    "operation": "replace_contents",
                    "fixture_path": "examples/loop-sandbox/invalid-json-fixture.json",
                    "expected_before_sha256": __import__("hashlib").sha256(before_text.encode("utf-8")).hexdigest(),
                    "replacement_contents": '{"status":"fixed_in_sandbox_only"}\n',
                },
                "human_required_when": ["repository_fixture_changed"],
            }
        ),
        encoding="utf-8",
    )
    plan = plan_loop_target_file(target, execute_stubbed=True)
    read_only = build_loop_read_only_execution_payload(plan, repo_root=tmp_path)
    gate = build_loop_read_only_evidence_gate(read_only["evidence_report"])
    execution = build_loop_read_only_command_execution_payload(read_only, gate, repo_root=tmp_path)
    diagnosis = build_loop_read_only_command_diagnosis_payload(execution)
    correction = build_loop_read_only_correction_plan_payload(diagnosis)

    mutation = build_loop_sandbox_file_mutation_payload(plan, correction, repo_root=tmp_path)

    assert mutation["ok"] is True
    assert mutation["schema"] == "promptbranch.loop.sandbox_file_mutation"
    assert mutation["status"] == "sandbox_file_mutation_applied"
    assert mutation["summary"]["sandbox_mutation_performed"] is True
    assert mutation["summary"]["repository_file_mutated"] is False
    assert mutation["safety"]["sandbox_only"] is True
    assert mutation["safety"]["project_source_mutation_performed"] is False
    assert mutation["safety"]["artifact_adoption_performed"] is False
    assert mutation["evidence"]["sandbox_fixture_before"] != mutation["evidence"]["sandbox_fixture_after"]
    assert mutation["evidence"]["repository_fixture_before"] == mutation["evidence"]["repository_fixture_after"]
    assert mutation["evidence"]["sandbox_workspace_deleted_after_evidence"] is True
    assert fixture.read_text(encoding="utf-8") == before_text


def test_loop_sandbox_file_mutation_blocks_non_sandbox_path(tmp_path: Path):
    from promptbranch_loop import build_loop_sandbox_file_mutation_payload

    readme = tmp_path / "README.md"
    readme.write_text("do not mutate\n", encoding="utf-8")
    plan = {
        "ok": True,
        "target_id": "bad-sandbox-path",
        "loop_id": "loop-bad-sandbox-path",
        "target_path": "target.json",
        "final_state": "SOLVED",
        "allowed_paths": ["README.md"],
        "sandbox_mutation": {
            "operation": "replace_contents",
            "fixture_path": "README.md",
            "replacement_contents": "changed\n",
        },
    }
    correction = {
        "schema": "promptbranch.loop.read_only_correction_plan",
        "status": "correction_plan_generated_failed_result",
        "summary": {"correction_plan_generated": True},
    }

    mutation = build_loop_sandbox_file_mutation_payload(plan, correction, repo_root=tmp_path)

    assert mutation["ok"] is False
    assert mutation["status"] == "sandbox_file_mutation_blocked"
    assert "blocked_non_sandbox_fixture_path" in mutation["blocked_reasons"]
    assert mutation["summary"]["sandbox_mutation_performed"] is False
    assert readme.read_text(encoding="utf-8") == "do not mutate\n"

def test_loop_sandbox_mutation_verification_passes_with_rollback_evidence(tmp_path: Path):
    from promptbranch_loop import (
        build_loop_read_only_command_diagnosis_payload,
        build_loop_read_only_command_execution_payload,
        build_loop_read_only_correction_plan_payload,
        build_loop_read_only_execution_payload,
        build_loop_sandbox_file_mutation_payload,
        build_loop_sandbox_mutation_verification_payload,
    )

    fixture = tmp_path / "examples" / "loop-sandbox" / "invalid-json-fixture.json"
    fixture.parent.mkdir(parents=True)
    fixture.write_text('{"status": "broken",\n', encoding="utf-8")
    before_text = fixture.read_text(encoding="utf-8")
    target = tmp_path / "target.json"
    target.write_text(
        json.dumps(
            {
                "schema": "promptbranch.loop.target",
                "schema_version": "1.0",
                "target_id": "sandbox-verification-test",
                "goal": "Verify sandbox mutation evidence and rollback cleanup.",
                "allowed_paths": ["examples/loop-sandbox/invalid-json-fixture.json"],
                "validation": {"commands": ["python3 -m json.tool examples/loop-sandbox/invalid-json-fixture.json"]},
                "sandbox_mutation": {
                    "operation": "replace_contents",
                    "fixture_path": "examples/loop-sandbox/invalid-json-fixture.json",
                    "expected_before_sha256": __import__("hashlib").sha256(before_text.encode("utf-8")).hexdigest(),
                    "replacement_contents": '{"status":"fixed_in_sandbox_only"}\n',
                },
                "human_required_when": ["sandbox_rollback_not_verified"],
            }
        ),
        encoding="utf-8",
    )
    plan = plan_loop_target_file(target, execute_stubbed=True)
    read_only = build_loop_read_only_execution_payload(plan, repo_root=tmp_path)
    gate = build_loop_read_only_evidence_gate(read_only["evidence_report"])
    execution = build_loop_read_only_command_execution_payload(read_only, gate, repo_root=tmp_path)
    diagnosis = build_loop_read_only_command_diagnosis_payload(execution)
    correction = build_loop_read_only_correction_plan_payload(diagnosis)
    mutation = build_loop_sandbox_file_mutation_payload(plan, correction, repo_root=tmp_path)

    verification = build_loop_sandbox_mutation_verification_payload(mutation)

    assert verification["ok"] is True
    assert verification["schema"] == "promptbranch.loop.sandbox_mutation_verification"
    assert verification["status"] == "sandbox_mutation_verification_passed"
    assert verification["summary"]["sandbox_mutation_verified"] is True
    assert verification["summary"]["rollback_verified"] is True
    assert verification["summary"]["files_mutated"] is False
    assert verification["safety"]["verification_only"] is True
    assert verification["safety"]["rollback_gate_verified"] is True
    assert verification["rollback_evidence"]["rollback_strategy"] == "delete_temporary_sandbox_workspace"
    assert verification["evidence_summary"]["repository_fixture_unchanged"] is True
    assert verification["evidence_summary"]["sandbox_fixture_changed"] is True
    assert fixture.read_text(encoding="utf-8") == before_text


def test_loop_sandbox_mutation_verification_blocks_missing_rollback_cleanup():
    from promptbranch_loop import build_loop_sandbox_mutation_verification_payload

    mutation = {
        "ok": True,
        "schema": "promptbranch.loop.sandbox_file_mutation",
        "status": "sandbox_file_mutation_applied",
        "target_id": "rollback-missing-test",
        "summary": {
            "sandbox_mutation_performed": True,
            "repository_file_mutated": False,
            "project_source_mutation_performed": False,
            "artifact_adoption_performed": False,
            "deployment_performed": False,
        },
        "safety": {
            "sandbox_file_mutation_performed": True,
            "project_source_mutation_performed": False,
            "artifact_adoption_performed": False,
            "deployment_performed": False,
            "kubernetes_mutation_performed": False,
        },
        "evidence": {
            "repository_fixture_before": {"sha256": "repo"},
            "repository_fixture_after": {"sha256": "repo"},
            "sandbox_fixture_before": {"sha256": "before"},
            "sandbox_fixture_after": {"sha256": "after"},
            "sandbox_workspace_deleted_after_evidence": False,
        },
    }

    verification = build_loop_sandbox_mutation_verification_payload(mutation)

    assert verification["ok"] is False
    assert verification["status"] == "sandbox_mutation_verification_blocked"
    assert "temporary_sandbox_workspace_deleted" in verification["blocked_reasons"]
    assert verification["summary"]["rollback_verified"] is False
    assert verification["side_effects_performed"] is False

