import json
import subprocess
import sys
from pathlib import Path

import promptbranch_cli

ROOT = Path(__file__).resolve().parents[1]


def test_loop_validate_cli_json_reports_target_valid(capsys):
    rc = promptbranch_cli.main([
        "loop",
        "validate",
        "--target",
        "examples/loop-targets/static-game-dry-run-target.json",
        "--json",
    ])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["action"] == "loop_validate"
    assert payload["target_id"] == "k8s-game-static-dry-run"
    assert payload["side_effects_performed"] is False


def test_loop_plan_cli_json_reports_dry_run_plan(capsys):
    rc = promptbranch_cli.main([
        "loop",
        "plan",
        "--target",
        "examples/loop-targets/static-game-dry-run-target.json",
        "--json",
    ])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["action"] == "loop_plan"
    assert payload["final_state"] == "SOLVED"
    assert payload["side_effects_performed"] is False
    assert payload["safety"]["commands_executed"] is False


def test_loop_run_cli_is_stubbed_dry_run_only(capsys):
    rc = promptbranch_cli.main([
        "loop",
        "run",
        "--target",
        "examples/loop-targets/static-game-dry-run-target.json",
        "--json",
    ])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["action"] == "loop_run"
    assert payload["dry_run"] is True
    assert payload["mode"] == "stubbed_control_flow_only"
    assert payload["safety"]["kubernetes_mutation_performed"] is False
    assert payload["safety"]["project_source_mutation_performed"] is False
    assert payload["safety"]["artifact_adoption_performed"] is False


def test_loop_run_text_shows_terminal_state(capsys):
    rc = promptbranch_cli.main([
        "loop",
        "run",
        "--target",
        "examples/loop-targets/static-game-dry-run-target.json",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "state=INTAKE" in out
    assert "final_state=SOLVED" in out
    assert "side_effects_performed=false" in out


def test_loop_run_state_only_prints_only_state_names(capsys):
    rc = promptbranch_cli.main([
        "loop",
        "run",
        "--target",
        "examples/loop-targets/static-game-dry-run-target.json",
        "--state-only",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    lines = out.splitlines()
    assert lines == [
        "INTAKE",
        "REQUIREMENTS_CHECK",
        "PLAN",
        "ACT_STUB",
        "TEST_STUB",
        "VERIFY_STUB",
        "DIAGNOSE_STUB",
        "CORRECT_STUB",
        "DEPLOY_GATE_STUB",
        "SOLVED",
    ]
    assert "state=" not in out
    assert "final_state" not in out
    assert "side_effects_performed" not in out


def test_loop_run_state_only_json_reports_states_without_events(capsys):
    rc = promptbranch_cli.main([
        "loop",
        "run",
        "--target",
        "examples/loop-targets/static-game-dry-run-target.json",
        "--state-only",
        "--json",
    ])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["action"] == "loop_run"
    assert payload["mode"] == "state_only"
    assert payload["states"] == [
        "INTAKE",
        "REQUIREMENTS_CHECK",
        "PLAN",
        "ACT_STUB",
        "TEST_STUB",
        "VERIFY_STUB",
        "DIAGNOSE_STUB",
        "CORRECT_STUB",
        "DEPLOY_GATE_STUB",
        "SOLVED",
    ]
    assert payload["dry_run"] is True
    assert payload["side_effects_performed"] is False
    assert payload["safety"]["commands_executed"] is False
    assert payload["safety"]["kubernetes_mutation_performed"] is False
    assert payload["safety"]["project_source_mutation_performed"] is False
    assert payload["safety"]["artifact_adoption_performed"] is False
    assert "events" not in payload


def test_loop_run_planned_actions_prints_state_action_gate_lines(capsys):
    rc = promptbranch_cli.main([
        "loop",
        "run",
        "--target",
        "examples/loop-targets/static-game-dry-run-target.json",
        "--planned-actions",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    lines = out.splitlines()
    assert lines[0] == "INTAKE | action=load target definition and create loop context | gate=target JSON parsed and target_id/goal are available | next=REQUIREMENTS_CHECK"
    assert any(line.startswith("TEST_STUB | action=list validation commands") for line in lines)
    assert lines[-1] == "SOLVED | action=stop the loop because the dry-run plan reaches its terminal success state | gate=final state is recorded without artifact adoption | next=none"
    assert "side_effects_performed" not in out


def test_loop_run_planned_actions_json_reports_actions_without_events(capsys):
    rc = promptbranch_cli.main([
        "loop",
        "run",
        "--target",
        "examples/loop-targets/static-game-dry-run-target.json",
        "--planned-actions",
        "--json",
    ])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["action"] == "loop_run"
    assert payload["mode"] == "planned_actions"
    assert payload["dry_run"] is True
    assert payload["side_effects_performed"] is False
    assert payload["safety"]["commands_executed"] is False
    assert payload["safety"]["kubernetes_mutation_performed"] is False
    assert payload["safety"]["project_source_mutation_performed"] is False
    assert payload["safety"]["artifact_adoption_performed"] is False
    assert "events" not in payload
    assert payload["actions"][0]["state"] == "INTAKE"
    assert payload["actions"][0]["execution_status"] == "not_executed_dry_run"


def test_loop_run_state_only_and_planned_actions_are_mutually_exclusive(capsys):
    rc = promptbranch_cli.main([
        "loop",
        "run",
        "--target",
        "examples/loop-targets/static-game-dry-run-target.json",
        "--state-only",
        "--planned-actions",
    ])
    assert rc == 2
    captured = capsys.readouterr()
    assert "mutually exclusive" in captured.err


def test_loop_run_read_only_execution_json_reports_no_commands_executed(capsys):
    rc = promptbranch_cli.main([
        "loop",
        "run",
        "--target",
        "examples/loop-targets/static-game-dry-run-target.json",
        "--read-only-execution",
        "--json",
    ])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["mode"] == "read_only_execution"
    assert payload["execution_mode"] == "local_read_only_preflight"
    assert payload["summary"]["commands_executed"] == 0
    assert payload["side_effects_performed"] is False
    assert payload["safety"]["commands_executed"] is False
    assert payload["safety"]["project_source_mutation_performed"] is False


def test_loop_run_read_only_execution_is_mutually_exclusive_with_presentation_modes(capsys):
    rc = promptbranch_cli.main([
        "loop",
        "run",
        "--target",
        "examples/loop-targets/static-game-dry-run-target.json",
        "--read-only-execution",
        "--planned-actions",
    ])
    assert rc == 2
    captured = capsys.readouterr()
    assert "mutually exclusive" in captured.err


def test_loop_run_read_only_execution_evidence_report_json(capsys):
    rc = promptbranch_cli.main([
        "loop",
        "run",
        "--target",
        "examples/loop-targets/static-game-dry-run-target.json",
        "--read-only-execution",
        "--evidence-report",
        "--json",
    ])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "promptbranch.loop.read_only_evidence_report"
    assert payload["status"] == "evidence_clean"
    assert payload["evidence_summary"]["commands_executed"] == 0
    assert payload["evidence_summary"]["skipped_command_count"] == payload["evidence_summary"]["declared_command_count"]
    assert payload["safety_assertions"]["project_source_mutation_performed"] is False


def test_loop_run_evidence_report_requires_read_only_execution(capsys):
    rc = promptbranch_cli.main([
        "loop",
        "run",
        "--target",
        "examples/loop-targets/static-game-dry-run-target.json",
        "--evidence-report",
    ])
    assert rc == 2
    captured = capsys.readouterr()
    assert "--evidence-report requires --read-only-execution" in captured.err



def test_loop_run_read_only_execution_evidence_gate_json(capsys):
    rc = promptbranch_cli.main([
        "loop",
        "run",
        "--target",
        "examples/loop-targets/static-game-dry-run-target.json",
        "--read-only-execution",
        "--evidence-gate",
        "--json",
    ])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "promptbranch.loop.read_only_evidence_gate"
    assert payload["status"] == "gate_passed"
    assert payload["decision"] == "continue_to_next_dry_run_step"
    assert payload["gate_summary"]["commands_executed"] == 0
    assert payload["gate_summary"]["failed_gate_count"] == 0
    assert payload["side_effects_performed"] is False


def test_loop_run_read_only_execution_evidence_gate_text(capsys):
    rc = promptbranch_cli.main([
        "loop",
        "run",
        "--target",
        "examples/loop-targets/static-game-dry-run-target.json",
        "--read-only-execution",
        "--evidence-gate",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "status=gate_passed" in out
    assert "decision=continue_to_next_dry_run_step" in out
    assert "commands_executed=0" in out
    assert "side_effects_performed=false" in out


def test_loop_run_evidence_gate_requires_read_only_execution(capsys):
    rc = promptbranch_cli.main([
        "loop",
        "run",
        "--target",
        "examples/loop-targets/static-game-dry-run-target.json",
        "--evidence-gate",
    ])
    assert rc == 2
    captured = capsys.readouterr()
    assert "--evidence-gate requires --read-only-execution" in captured.err


def test_loop_run_evidence_report_and_gate_are_mutually_exclusive(capsys):
    rc = promptbranch_cli.main([
        "loop",
        "run",
        "--target",
        "examples/loop-targets/static-game-dry-run-target.json",
        "--read-only-execution",
        "--evidence-report",
        "--evidence-gate",
    ])
    assert rc == 2
    captured = capsys.readouterr()
    assert "--evidence-report and --evidence-gate are mutually exclusive" in captured.err


def test_loop_run_execute_read_only_validation_cli_json_executes_one_allowlisted_command():
    result = subprocess.run(
        [
            sys.executable,
            "promptbranch_cli.py",
            "loop",
            "run",
            "--target",
            "examples/loop-targets/read-only-validation-command-target.json",
            "--read-only-execution",
            "--evidence-gate",
            "--execute-read-only-validation",
            "--json",
        ],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["schema"] == "promptbranch.loop.read_only_command_execution"
    assert payload["summary"]["commands_executed"] == 1
    assert payload["summary"]["mutation_detected"] is False
    assert payload["command_evidence"][0]["execution_status"] == "executed_read_only_validation_passed"


def test_loop_run_execute_read_only_validation_requires_evidence_gate(capsys):
    rc = promptbranch_cli.main([
        "loop",
        "run",
        "--target",
        "examples/loop-targets/read-only-validation-command-target.json",
        "--read-only-execution",
        "--execute-read-only-validation",
    ])
    captured = capsys.readouterr()
    assert rc == 2
    assert "--execute-read-only-validation requires --read-only-execution --evidence-gate" in captured.err


def test_loop_run_diagnose_read_only_result_cli_json_classifies_passed_result():
    result = subprocess.run(
        [
            sys.executable,
            "promptbranch_cli.py",
            "loop",
            "run",
            "--target",
            "examples/loop-targets/read-only-validation-command-target.json",
            "--read-only-execution",
            "--evidence-gate",
            "--execute-read-only-validation",
            "--diagnose-read-only-result",
            "--json",
        ],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema"] == "promptbranch.loop.read_only_command_diagnosis"
    assert payload["status"] == "diagnosis_passed_result"
    assert payload["result_classification"] == "passed"
    assert payload["summary"]["correction_plan_generated"] is False
    assert payload["safety"]["files_mutated"] is False


def test_loop_run_diagnose_read_only_result_requires_execution_flag(capsys):
    rc = promptbranch_cli.main([
        "loop",
        "run",
        "--target",
        "examples/loop-targets/read-only-validation-command-target.json",
        "--read-only-execution",
        "--evidence-gate",
        "--diagnose-read-only-result",
    ])
    captured = capsys.readouterr()
    assert rc == 2
    assert "--diagnose-read-only-result requires --execute-read-only-validation" in captured.err


def test_loop_run_generate_correction_plan_cli_json_from_passed_result(capsys):
    rc = promptbranch_cli.main([
        "loop",
        "run",
        "--target",
        "examples/loop-targets/read-only-validation-command-target.json",
        "--read-only-execution",
        "--evidence-gate",
        "--execute-read-only-validation",
        "--diagnose-read-only-result",
        "--generate-correction-plan",
        "--json",
    ])
    captured = capsys.readouterr()
    assert rc == 0, captured.err + captured.out
    payload = json.loads(captured.out)
    assert payload["schema"] == "promptbranch.loop.read_only_correction_plan"
    assert payload["status"] == "correction_plan_not_required"
    assert payload["source_result_classification"] == "passed"
    assert payload["summary"]["correction_plan_generated"] is False
    assert payload["summary"]["commands_executed"] == 0
    assert payload["summary"]["files_mutated"] is False
    assert payload["safety"]["correction_plan_only"] is True


def test_loop_run_generate_correction_plan_requires_diagnosis_flag(capsys):
    rc = promptbranch_cli.main([
        "loop",
        "run",
        "--target",
        "examples/loop-targets/read-only-validation-command-target.json",
        "--read-only-execution",
        "--evidence-gate",
        "--execute-read-only-validation",
        "--generate-correction-plan",
    ])
    captured = capsys.readouterr()
    assert rc == 2
    assert "--generate-correction-plan requires --diagnose-read-only-result" in captured.err


def test_loop_run_execute_sandbox_mutation_cli_json_mutates_temp_fixture_only(capsys):
    before = Path("examples/loop-sandbox/invalid-json-fixture.json").read_text(encoding="utf-8")
    rc = promptbranch_cli.main([
        "loop",
        "run",
        "--target",
        "examples/loop-targets/sandboxed-file-mutation-target.json",
        "--read-only-execution",
        "--evidence-gate",
        "--execute-read-only-validation",
        "--diagnose-read-only-result",
        "--generate-correction-plan",
        "--execute-sandbox-mutation",
        "--json",
    ])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "promptbranch.loop.sandbox_file_mutation"
    assert payload["status"] == "sandbox_file_mutation_applied"
    assert payload["summary"]["sandbox_mutation_performed"] is True
    assert payload["summary"]["repository_file_mutated"] is False
    assert payload["safety"]["sandbox_file_mutation_performed"] is True
    assert payload["safety"]["repository_file_mutation_performed"] is False
    assert payload["safety"]["project_source_mutation_performed"] is False
    assert Path("examples/loop-sandbox/invalid-json-fixture.json").read_text(encoding="utf-8") == before


def test_loop_run_execute_sandbox_mutation_requires_correction_plan(capsys):
    rc = promptbranch_cli.main([
        "loop",
        "run",
        "--target",
        "examples/loop-targets/sandboxed-file-mutation-target.json",
        "--read-only-execution",
        "--evidence-gate",
        "--execute-read-only-validation",
        "--diagnose-read-only-result",
        "--execute-sandbox-mutation",
    ])
    assert rc == 2
    captured = capsys.readouterr()
    assert "--execute-sandbox-mutation requires --generate-correction-plan" in captured.err
