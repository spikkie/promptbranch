#!/usr/bin/env python3
"""Execute and verify the mandatory v0.1.104 sandbox rollback release gate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

EXPECTED_GATES = (
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
)


def _result(*, ok: bool, checks: dict[str, bool], payload: dict[str, Any] | None, error: str | None = None) -> dict[str, Any]:
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "schema": "promptbranch.release_control.sandbox_mutation_rollback_gate",
        "schema_version": "1.0",
        "ok": ok,
        "status": "sandbox_mutation_verified_and_rolled_back" if ok else "sandbox_mutation_rollback_gate_failed",
        "decision": "stop_after_verified_sandbox_rollback_evidence" if ok else "stop_for_operator_review",
        "mandatory_release_gate": True,
        "gate_count": len(EXPECTED_GATES),
        "passed_gate_count": len(EXPECTED_GATES) - len(failed),
        "failed_gate_count": len(failed),
        "failed_gates": failed,
        "checks": checks,
        "sandbox_payload": payload,
        "error": error,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    args = parser.parse_args()
    repo = args.repo.expanduser().resolve()
    command = [
        sys.executable,
        str(repo / "promptbranch_cli.py"),
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
    ]
    completed = subprocess.run(command, cwd=repo, text=True, capture_output=True, timeout=120)
    payload: dict[str, Any] | None = None
    error: str | None = None
    try:
        decoded = json.loads(completed.stdout)
        if isinstance(decoded, dict):
            payload = decoded
        else:
            error = "sandbox command JSON root is not an object"
    except Exception as exc:
        error = f"sandbox command did not emit valid JSON: {exc}"

    gate_payload = payload.get("verification_gate") if isinstance(payload, dict) and isinstance(payload.get("verification_gate"), dict) else {}
    gates = gate_payload.get("gates") if isinstance(gate_payload.get("gates"), list) else []
    observed = {
        str(item.get("name")): item.get("passed") is True
        for item in gates
        if isinstance(item, dict) and item.get("name")
    }
    summary = payload.get("summary") if isinstance(payload, dict) and isinstance(payload.get("summary"), dict) else {}
    safety = payload.get("safety") if isinstance(payload, dict) and isinstance(payload.get("safety"), dict) else {}
    evidence = payload.get("evidence") if isinstance(payload, dict) and isinstance(payload.get("evidence"), dict) else {}

    checks = {name: observed.get(name) is True for name in EXPECTED_GATES}
    checks.update(
        {
            "command_exit_zero": completed.returncode == 0,
            "payload_ok": isinstance(payload, dict) and payload.get("ok") is True,
            "terminal_status_exact": isinstance(payload, dict) and payload.get("status") == "sandbox_mutation_verified_and_rolled_back",
            "gate_count_exact": gate_payload.get("gate_count") == 13,
            "passed_gate_count_exact": gate_payload.get("passed_gate_count") == 13,
            "failed_gate_count_zero": gate_payload.get("failed_gate_count") == 0,
            "sandbox_mutation_verified": summary.get("sandbox_mutation_verified") is True,
            "sandbox_validation_passed_summary": summary.get("sandbox_validation_passed") is True,
            "sandbox_rollback_succeeded": summary.get("sandbox_rollback_succeeded") is True,
            "repository_file_not_mutated": summary.get("repository_file_mutated") is False,
            "project_source_not_mutated": safety.get("project_source_mutation_performed") is False,
            "artifact_not_adopted": safety.get("artifact_adoption_performed") is False,
            "deployment_not_performed": safety.get("deployment_performed") is False,
            "before_after_differ": evidence.get("sandbox_fixture_before") != evidence.get("sandbox_fixture_after_mutation"),
            "rollback_snapshot_equal": evidence.get("sandbox_fixture_before") == evidence.get("sandbox_fixture_after_rollback"),
            "repository_snapshot_equal": evidence.get("repository_fixture_before") == evidence.get("repository_fixture_after"),
            "workspace_deleted": evidence.get("sandbox_workspace_deleted_after_evidence") is True,
        }
    )
    ok = error is None and all(checks.values())
    result = _result(ok=ok, checks=checks, payload=payload, error=error or (completed.stderr.strip() or None if not ok else None))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
