from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from promptbranch_application_pilot import (
    ApplicationPilotError,
    DEFAULT_CONFIG,
    build_application_pilot_plan,
    build_application_pilot_validation,
    load_application_pilot_definition,
    validate_application_pilot_definition,
)

ROOT = Path(__file__).resolve().parents[1]


def _target_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "k8s-game-mvp"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "README.md").write_text("external application pilot\n", encoding="utf-8")
    return repo


def _snapshot(root: Path) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            result[path.relative_to(root).as_posix()] = path.read_bytes()
    return result


def test_default_pilot_definition_is_valid_and_read_only() -> None:
    result = build_application_pilot_validation(ROOT)
    assert result["ok"] is True
    assert result["status"] == "pilot_definition_valid"
    assert result["definition"]["schema"] == "promptbranch.application.pilot"
    assert result["definition"]["pilot"]["application_repo_id"] == "k8s-game-mvp"
    assert result["definition"]["execution_plan"] == {"mode": "read_only", "max_iterations": 1}
    assert result["definition"]["authority"]["mutation_allowed"] is False
    assert result["definition"]["authority"]["deployment_allowed"] is False
    assert result["safety"]["git_commands_executed"] is False


def test_pilot_plan_requires_separate_established_repository_and_mutates_nothing(tmp_path: Path) -> None:
    target = _target_repo(tmp_path)
    before = _snapshot(target)
    result = build_application_pilot_plan(ROOT, target)
    after = _snapshot(target)

    assert result["ok"] is True
    assert result["status"] == "pilot_bootstrap_plan_ready"
    assert result["repo_binding"]["control_and_target_distinct"] is True
    assert result["repo_binding"]["repo_marker_present"] is True
    assert result["bootstrap"]["mutation_performed"] is False
    assert result["execution_plan"]["commands_executed"] == []
    assert result["execution_plan"]["steps"][-1]["action"] == "stop_before_mutation"
    assert result["safety"]["target_repo_mutated"] is False
    assert result["safety"]["git_commands_executed"] is False
    assert result["safety"]["git_mutation_performed"] is False
    assert result["safety"]["project_source_mutated"] is False
    assert result["safety"]["deployment_performed"] is False
    assert result["safety"]["artifact_adopted"] is False
    assert before == after


def test_pilot_plan_proposes_target_architecture_dod_and_tests(tmp_path: Path) -> None:
    target = _target_repo(tmp_path)
    result = build_application_pilot_plan(ROOT, target)
    proposed = set(result["bootstrap"]["proposed_paths"])
    assert "docs/target.md" in proposed
    assert ".promptbranch-ai.json" in proposed
    assert "docs/architecture.md" in proposed
    assert "docs/definition-of-done.md" in proposed
    assert "tests/test_static_game.py" in proposed
    assert result["tests"]["commands"] == [["python", "-m", "pytest", "-q", "tests/test_static_game.py"]]
    actions = [step["action"] for step in result["execution_plan"]["steps"]]
    assert actions == [
        "inspect_external_repository",
        "bind_application_identity",
        "propose_target_contract",
        "propose_application_architecture",
        "propose_definition_of_done",
        "propose_application_tests",
        "stop_before_mutation",
    ]


def test_pilot_plan_rejects_control_repo_as_target() -> None:
    with pytest.raises(ApplicationPilotError, match="must be separate"):
        build_application_pilot_plan(ROOT, ROOT)


def test_pilot_plan_rejects_directory_without_repository_marker(tmp_path: Path) -> None:
    target = tmp_path / "plain-dir"
    target.mkdir()
    with pytest.raises(ApplicationPilotError, match="required marker missing"):
        build_application_pilot_plan(ROOT, target)


def test_pilot_contract_rejects_mutation_authority() -> None:
    payload = json.loads((ROOT / DEFAULT_CONFIG).read_text(encoding="utf-8"))
    payload["authority"]["mutation_allowed"] = True
    with pytest.raises(ApplicationPilotError, match="mutation_allowed=false"):
        validate_application_pilot_definition(payload)


def test_pilot_contract_rejects_shell_validation_commands() -> None:
    payload = json.loads((ROOT / DEFAULT_CONFIG).read_text(encoding="utf-8"))
    payload["tests"]["commands"] = [["bash", "-lc", "pytest -q"]]
    with pytest.raises(ApplicationPilotError, match="may not invoke a shell"):
        validate_application_pilot_definition(payload)


def test_application_pilot_cli_validate_json() -> None:
    result = subprocess.run(
        [sys.executable, "promptbranch_cli.py", "application", "pilot", "validate", "--control-repo-path", str(ROOT), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["status"] == "pilot_definition_valid"


def test_application_pilot_cli_plan_json(tmp_path: Path) -> None:
    target = _target_repo(tmp_path)
    result = subprocess.run(
        [sys.executable, "promptbranch_cli.py", "application", "pilot", "plan", "--control-repo-path", str(ROOT), "--target-repo", str(target), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["status"] == "pilot_bootstrap_plan_ready"
    assert payload["safety"]["git_commands_executed"] is False


def test_application_pilot_cli_blocks_non_repository_target_without_git_commands(tmp_path: Path) -> None:
    target = tmp_path / "not-a-repo"
    target.mkdir()
    result = subprocess.run(
        [sys.executable, "promptbranch_cli.py", "application", "pilot", "plan", "--control-repo-path", str(ROOT), "--target-repo", str(target), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "pilot_bootstrap_blocked"
    assert payload["safety"]["git_commands_executed"] is False
    assert "fatal: not a git repository" not in result.stderr
