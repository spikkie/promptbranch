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
