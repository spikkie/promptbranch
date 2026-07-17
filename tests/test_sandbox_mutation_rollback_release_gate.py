from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify-sandbox-mutation-rollback-release-gate.py"

EXPECTED_GATES = {
    "correction_plan_schema_valid",
    "correction_plan_generated",
    "sandbox_fixture_allowlisted",
    "mutation_operation_allowlisted",
    "before_hash_matches",
    "after_hash_matches",
    "mutation_result_verified",
    "sandbox_validation_passed",
    "sandbox_validation_read_only",
    "repository_fixture_unchanged",
    "rollback_attempted",
    "rollback_restored_before_snapshot",
    "sandbox_workspace_deleted",
}


def test_release_gate_executes_exact_sandbox_proof() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(ROOT)],
        text=True,
        capture_output=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["status"] == "sandbox_mutation_verified_and_rolled_back"
    assert payload["mandatory_release_gate"] is True
    assert payload["gate_count"] == 13
    assert payload["passed_gate_count"] == 13
    assert payload["failed_gate_count"] == 0
    assert payload["failed_gates"] == []
    sandbox = payload["sandbox_payload"]
    assert {item["name"] for item in sandbox["verification_gate"]["gates"]} == EXPECTED_GATES
    assert all(item["passed"] is True for item in sandbox["verification_gate"]["gates"])
    assert sandbox["evidence"]["sandbox_fixture_before"] == sandbox["evidence"]["sandbox_fixture_after_rollback"]
    assert sandbox["evidence"]["repository_fixture_before"] == sandbox["evidence"]["repository_fixture_after"]
    assert sandbox["evidence"]["sandbox_workspace_deleted_after_evidence"] is True
