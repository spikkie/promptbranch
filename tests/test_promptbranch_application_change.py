from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import promptbranch_application_change as change_module
from promptbranch_application_change import (
    ApplicationChangeError,
    DEFAULT_CONFIG,
    build_application_change_plan,
    execute_application_change,
    load_application_change_definition,
    rollback_application_change,
    validate_application_change_definition,
)

ROOT = Path(__file__).resolve().parents[1]


def _target_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "k8s-game-mvp"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "README.md").write_text("external application\n", encoding="utf-8")
    return repo


def _snapshot(root: Path) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and ".git" not in path.parts:
            result[path.relative_to(root).as_posix()] = path.read_bytes()
    return result


def _copy_config(control: Path, payload: dict) -> str:
    rel = "change.json"
    (control / rel).write_text(json.dumps(payload), encoding="utf-8")
    return rel


def test_default_change_definition_is_bounded_and_requires_human_authorization() -> None:
    definition = load_application_change_definition(ROOT)
    assert definition["schema"] == "promptbranch.application.change"
    assert definition["change"]["pilot_id"] == "k8s-game-mvp"
    assert definition["authorization"]["mode"] == "explicit_cli_exact_change_id"
    assert definition["authority"]["target_file_mutation_allowed"] is True
    assert definition["authority"]["git_commands_allowed"] is False
    assert definition["authority"]["application_test_execution_allowed"] is False
    assert len(definition["operations"]) == 7
    assert all(item["action"] == "write_file" for item in definition["operations"])


def test_change_plan_is_read_only_and_captures_preconditions(tmp_path: Path) -> None:
    target = _target_repo(tmp_path)
    before = _snapshot(target)
    result = build_application_change_plan(ROOT, target)
    after = _snapshot(target)
    assert result["ok"] is True
    assert result["status"] == "controlled_change_plan_ready"
    assert result["authorization"]["required"] is True
    assert result["authorization"]["required_change_id"] == "k8s-game-mvp-bootstrap-contracts"
    assert result["safety"]["read_only"] is True
    assert result["safety"]["target_repo_mutated"] is False
    assert result["safety"]["git_commands_executed"] is False
    assert result["safety"]["application_tests_executed"] is False
    assert before == after


def test_change_apply_requires_execute_and_exact_change_id(tmp_path: Path) -> None:
    target = _target_repo(tmp_path)
    with pytest.raises(ApplicationChangeError, match="--execute"):
        execute_application_change(ROOT, target)
    with pytest.raises(ApplicationChangeError, match="--authorize-change"):
        execute_application_change(ROOT, target, execute=True, authorized_change_id="wrong")
    assert _snapshot(target) == {"README.md": b"external application\n"}


def test_change_apply_writes_only_declared_paths_and_persists_evidence(tmp_path: Path) -> None:
    target = _target_repo(tmp_path)
    result = execute_application_change(
        ROOT,
        target,
        execute=True,
        authorized_change_id="k8s-game-mvp-bootstrap-contracts",
    )
    assert result["ok"] is True
    assert result["status"] == "controlled_change_applied_and_verified"
    assert result["operation_count"] == 7
    assert result["safety"]["human_authorization_verified"] is True
    assert result["safety"]["git_commands_executed"] is False
    assert result["safety"]["git_publication_performed"] is False
    assert result["safety"]["deployment_performed"] is False
    assert result["safety"]["application_tests_executed"] is False
    evidence_path = Path(result["evidence_path"])
    assert evidence_path.is_file()
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence["status"] == "applied_and_verified"
    assert evidence["rollback"]["required"] is True
    assert (target / "docs/target.md").is_file()
    assert (target / "tests/test_static_game.py").is_file()
    assert not (target / "index.html").exists()


def test_explicit_rollback_restores_exact_before_snapshot(tmp_path: Path) -> None:
    target = _target_repo(tmp_path)
    before = _snapshot(target)
    applied = execute_application_change(
        ROOT,
        target,
        execute=True,
        authorized_change_id="k8s-game-mvp-bootstrap-contracts",
    )
    result = rollback_application_change(
        target,
        applied["evidence_path"],
        execute=True,
        authorized_change_id="k8s-game-mvp-bootstrap-contracts",
    )
    assert result["ok"] is True
    assert result["status"] == "controlled_change_rolled_back_and_verified"
    assert result["rollback"]["succeeded"] is True
    assert _snapshot(target) == before


def test_rollback_refuses_to_clobber_post_apply_drift(tmp_path: Path) -> None:
    target = _target_repo(tmp_path)
    applied = execute_application_change(
        ROOT,
        target,
        execute=True,
        authorized_change_id="k8s-game-mvp-bootstrap-contracts",
    )
    (target / "docs/target.md").write_text("operator changed this\n", encoding="utf-8")
    with pytest.raises(ApplicationChangeError, match="post-apply drift"):
        rollback_application_change(
            target,
            applied["evidence_path"],
            execute=True,
            authorized_change_id="k8s-game-mvp-bootstrap-contracts",
        )
    assert (target / "docs/target.md").read_text(encoding="utf-8") == "operator changed this\n"


def test_precondition_mismatch_blocks_without_mutation(tmp_path: Path) -> None:
    target = _target_repo(tmp_path)
    (target / "VERSION").write_text("existing\n", encoding="utf-8")
    before = _snapshot(target)
    with pytest.raises(ApplicationChangeError, match="precondition failed"):
        execute_application_change(
            ROOT,
            target,
            execute=True,
            authorized_change_id="k8s-game-mvp-bootstrap-contracts",
        )
    assert _snapshot(target) == before


def test_symlink_target_is_rejected(tmp_path: Path) -> None:
    target = _target_repo(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (target / "docs").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ApplicationChangeError, match="symlink"):
        build_application_change_plan(ROOT, target)


def test_mid_apply_failure_automatically_rolls_back(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = _target_repo(tmp_path)
    before = _snapshot(target)
    original = change_module._atomic_write
    calls = {"count": 0}

    def fail_after_parent_creation(path: Path, data: bytes, *, mode: int = 0o644):
        calls["count"] += 1
        if calls["count"] == 3:
            path.parent.mkdir(parents=True, exist_ok=True)
            raise OSError("simulated write failure after parent creation")
        return original(path, data, mode=mode)

    monkeypatch.setattr(change_module, "_atomic_write", fail_after_parent_creation)
    with pytest.raises(ApplicationChangeError, match="automatic rollback succeeded"):
        execute_application_change(
            ROOT,
            target,
            execute=True,
            authorized_change_id="k8s-game-mvp-bootstrap-contracts",
        )
    assert _snapshot(target) == before
    assert not (target / ".promptbranch").exists()


def test_exact_sha_replace_and_rollback_preserve_original_bytes(tmp_path: Path) -> None:
    control = tmp_path / "control"
    control.mkdir()
    target = _target_repo(tmp_path)
    existing = target / "README.md"
    original = existing.read_bytes()
    import hashlib
    payload = json.loads((ROOT / DEFAULT_CONFIG).read_text(encoding="utf-8"))
    payload["change"]["id"] = "replace-readme"
    payload["operations"] = [{
        "id": "replace",
        "action": "write_file",
        "path": "README.md",
        "precondition": {"state": "exact_sha256", "sha256": hashlib.sha256(original).hexdigest()},
        "content": "replacement\n",
    }]
    config = _copy_config(control, payload)
    applied = execute_application_change(control, target, config=config, execute=True, authorized_change_id="replace-readme")
    assert existing.read_text(encoding="utf-8") == "replacement\n"
    rollback_application_change(target, applied["evidence_path"], execute=True, authorized_change_id="replace-readme")
    assert existing.read_bytes() == original


def test_contract_rejects_git_or_test_authority() -> None:
    payload = json.loads((ROOT / DEFAULT_CONFIG).read_text(encoding="utf-8"))
    payload["authority"]["git_commands_allowed"] = True
    with pytest.raises(ApplicationChangeError, match="git_commands_allowed"):
        validate_application_change_definition(payload)
    payload = json.loads((ROOT / DEFAULT_CONFIG).read_text(encoding="utf-8"))
    payload["authority"]["application_test_execution_allowed"] = True
    with pytest.raises(ApplicationChangeError, match="application_test_execution_allowed"):
        validate_application_change_definition(payload)


def test_contract_rejects_unbounded_content() -> None:
    payload = json.loads((ROOT / DEFAULT_CONFIG).read_text(encoding="utf-8"))
    payload["operations"][0]["content"] = "x" * (change_module.MAX_OPERATION_CONTENT_BYTES + 1)
    with pytest.raises(ApplicationChangeError, match="bounded size limit"):
        validate_application_change_definition(payload)


def test_application_change_cli_plan_apply_and_rollback(tmp_path: Path) -> None:
    target = _target_repo(tmp_path)
    base = [sys.executable, "promptbranch_cli.py", "application", "change"]
    plan = subprocess.run(
        [*base, "plan", "--control-repo-path", str(ROOT), "--target-repo", str(target), "--json"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    assert plan.returncode == 0, plan.stderr + plan.stdout
    assert json.loads(plan.stdout)["safety"]["target_repo_mutated"] is False

    blocked = subprocess.run(
        [*base, "apply", "--control-repo-path", str(ROOT), "--target-repo", str(target), "--authorize-change", "k8s-game-mvp-bootstrap-contracts", "--json"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    assert blocked.returncode == 1
    assert json.loads(blocked.stdout)["status"] == "controlled_change_blocked"

    applied = subprocess.run(
        [*base, "apply", "--control-repo-path", str(ROOT), "--target-repo", str(target), "--execute", "--authorize-change", "k8s-game-mvp-bootstrap-contracts", "--json"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    assert applied.returncode == 0, applied.stderr + applied.stdout
    applied_payload = json.loads(applied.stdout)
    assert applied_payload["status"] == "controlled_change_applied_and_verified"

    rolled = subprocess.run(
        [*base, "rollback", "--target-repo", str(target), "--evidence", applied_payload["evidence_path"], "--execute", "--authorize-change", "k8s-game-mvp-bootstrap-contracts", "--json"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    assert rolled.returncode == 0, rolled.stderr + rolled.stdout
    assert json.loads(rolled.stdout)["status"] == "controlled_change_rolled_back_and_verified"
