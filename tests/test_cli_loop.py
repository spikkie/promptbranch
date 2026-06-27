import json

import promptbranch_cli


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
