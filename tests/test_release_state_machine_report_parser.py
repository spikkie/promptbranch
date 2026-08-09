from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from promptbranch_release_state_machine import (
    TEST_REPORT_SCHEMA,
    TEST_REPORT_SCHEMA_VERSION,
    SubprocessReleaseExecutor,
    _parse_json_documents,
    _select_candidate_test_report,
    _test_report_counts,
)


VERSION = "v0.1.126"


def _full_report(*, ok: bool = True, failed: int = 0, skipped: int = 0) -> dict:
    states = {
        "agent.agent_tool_call_test_smoke": "passed" if failed == 0 else "failed",
        "validation.execution_envelope_validation_gate": "passed" if failed == 0 else "failed",
        "validation.compileall": "passed" if skipped == 0 else "skipped:fail_fast",
    }
    total = 53
    passed = total - failed - skipped
    return {
        "ok": ok,
        "schema": TEST_REPORT_SCHEMA,
        "schema_version": TEST_REPORT_SCHEMA_VERSION,
        "action": "test_suite",
        "profile": "full",
        "version": VERSION,
        "browser": {"ok": True},
        "agent": {"ok": ok},
        "progress": {
            "enabled": True,
            "fail_fast": True,
            "total_units": total,
            "completed_units": total,
            "passed_units": passed,
            "failed_units": failed,
            "skipped_units": skipped,
            "states": states,
            "unresolved_steps": [],
        },
        "safety": {
            "write_tools_blocked": True,
            "model_has_execution_authority": False,
            "source_or_artifact_mutation_allowed": False,
        },
    }


def test_stream_parser_does_not_return_nested_safety_object_as_document() -> None:
    report = _full_report()
    stdout = (
        "pb_test_progress: status=completed completed=53/53\n"
        + json.dumps(report, indent=2)
        + "\n"
    )

    documents = _parse_json_documents(stdout)

    assert len(documents) == 1
    assert documents[0]["action"] == "test_suite"
    assert documents[0]["safety"]["write_tools_blocked"] is True


def test_report_selector_uses_action_profile_version_and_rejects_unrelated_json() -> None:
    report = _full_report()
    stdout = (
        json.dumps({"status": "diagnostic", "ok": True})
        + "\n"
        + json.dumps(report)
        + "\n"
        + json.dumps({
            "write_tools_blocked": True,
            "model_has_execution_authority": False,
            "source_or_artifact_mutation_allowed": False,
        })
    )

    selected = _select_candidate_test_report(stdout, profile="full", version=VERSION)

    assert selected["ok"] is True
    assert selected["status"] == "candidate_test_report_selected"
    assert selected["match_count"] == 1
    assert selected["report"] == report


def test_report_selector_distinguishes_missing_ambiguous_and_invalid() -> None:
    missing = _select_candidate_test_report(
        json.dumps({"write_tools_blocked": True}),
        profile="full",
        version=VERSION,
    )
    assert missing["status"] == "candidate_test_report_missing"
    assert missing["failure_code"] == "candidate_test_report_missing"

    report = _full_report()
    ambiguous = _select_candidate_test_report(
        json.dumps(report) + "\n" + json.dumps(report),
        profile="full",
        version=VERSION,
    )
    assert ambiguous["status"] == "candidate_test_report_ambiguous"
    assert ambiguous["failure_code"] == "candidate_test_report_ambiguous"

    invalid_report = dict(report)
    invalid_report.pop("schema")
    invalid = _select_candidate_test_report(
        json.dumps(invalid_report),
        profile="full",
        version=VERSION,
    )
    assert invalid["status"] == "candidate_test_report_invalid"
    assert invalid["failure_code"] == "candidate_test_report_invalid"
    assert "schema_mismatch" in invalid["errors"]


def test_report_counts_persist_units_and_failed_validation_group() -> None:
    counts = _test_report_counts(_full_report(ok=False, failed=3, skipped=2), profile="full")

    assert counts == {
        "completed": 53,
        "passed": 48,
        "failed": 3,
        "skipped": 2,
        "failed_group": "execution_envelope_validation_gate",
        "failed_groups": ["execution_envelope_validation_gate"],
        "failed_steps": [
            "agent.agent_tool_call_test_smoke",
            "validation.execution_envelope_validation_gate",
        ],
    }


def test_subprocess_executor_persists_selected_report_and_hashes(tmp_path: Path, monkeypatch) -> None:
    report = _full_report(ok=False, failed=3, skipped=2)
    stdout = "progress line\n" + json.dumps(report, indent=2) + "\n"
    stderr = ""

    class Machine:
        attempt_dir = tmp_path / "attempt"
        config = SimpleNamespace(
            candidate_python=None,
            profile="full",
            version=VERSION,
            test_timeout=3600.0,
            profile_dir=tmp_path / "profile",
        )

    extracted = Machine.attempt_dir / "runtime" / "extracted"
    extracted.mkdir(parents=True)
    (extracted / "promptbranch_cli.py").write_text("# fixture\n", encoding="utf-8")
    runtime = {
        "candidate_pytest_version": "9.0.2",
        "candidate_service_base_url": "http://127.0.0.1:18590",
        "candidate_compose_project": "pb-candidate-fixture",
        "candidate_service_image": "promptbranch-candidate:fixture",
        "candidate_service_port": 18590,
        "candidate_container_id": "container",
        "accepted_runtime_before": {},
    }
    record = {
        "attempt_id": "fixture-attempt",
        "artifact": {"sha256": "a" * 64},
        "evidence": {"RUNTIME_PREPARED": runtime},
    }

    monkeypatch.setattr(
        "promptbranch_release_state_machine.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(stdout=stdout, stderr=stderr, returncode=1),
    )

    result = SubprocessReleaseExecutor().run_tests(Machine(), record)

    assert result["ok"] is False
    assert result["failure_code"] == "candidate_test_failed"
    assert result["report_selected"] is True
    assert result["report_schema"] == TEST_REPORT_SCHEMA
    assert result["report_schema_version"] == TEST_REPORT_SCHEMA_VERSION
    assert result["completed"] == 53
    assert result["passed"] == 48
    assert result["failed"] == 3
    assert result["skipped"] == 2
    assert result["failed_group"] == "execution_envelope_validation_gate"
    assert result["stdout_sha256"] == hashlib.sha256(stdout.encode()).hexdigest()
    assert result["stderr_sha256"] == hashlib.sha256(stderr.encode()).hexdigest()
    assert Path(result["report_path"]).is_file()
    assert json.loads(Path(result["report_path"]).read_text(encoding="utf-8"))["action"] == "test_suite"


def test_missing_report_never_claims_failed_count_zero(tmp_path: Path, monkeypatch) -> None:
    stdout = json.dumps({"write_tools_blocked": True}) + "\n"

    class Machine:
        attempt_dir = tmp_path / "attempt"
        config = SimpleNamespace(
            candidate_python=None,
            profile="full",
            version=VERSION,
            test_timeout=3600.0,
            profile_dir=tmp_path / "profile",
        )

    extracted = Machine.attempt_dir / "runtime" / "extracted"
    extracted.mkdir(parents=True)
    (extracted / "promptbranch_cli.py").write_text("# fixture\n", encoding="utf-8")
    record = {
        "attempt_id": "fixture-attempt",
        "artifact": {"sha256": "a" * 64},
        "evidence": {"RUNTIME_PREPARED": {"candidate_pytest_version": "9.0.2"}},
    }
    monkeypatch.setattr(
        "promptbranch_release_state_machine.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(stdout=stdout, stderr="", returncode=1),
    )

    result = SubprocessReleaseExecutor().run_tests(Machine(), record)

    assert result["status"] == "candidate_test_report_missing"
    assert result["failure_code"] == "candidate_test_report_missing"
    assert result["failed"] is None
    assert result["skipped"] is None
    assert result["report_selected"] is False


def test_acceptance_result_selector_ignores_nested_current_consistency_object() -> None:
    from promptbranch_release_state_machine import _select_accept_candidate_result

    payload = {
        "ok": True,
        "action": "artifact_accept_candidate",
        "status": "accepted_candidate",
        "artifact_current": {
            "ok": True,
            "action": "artifact_current_all",
            "status": "artifact_registry_loaded",
            "consistency": {
                "registry_current_matches_state_artifact": True,
                "state_source_matches_state_artifact": True,
            },
        },
        "candidate_registry_entry": {"accepted": True},
        "adoption_performed": True,
    }
    stdout = "diagnostic before\n" + json.dumps(payload, indent=2) + "\n"

    selected = _select_accept_candidate_result(stdout)

    assert selected["ok"] is True
    assert selected["match_count"] == 1
    assert selected["result"]["action"] == "artifact_accept_candidate"
    assert selected["result"]["status"] == "accepted_candidate"


def test_current_status_selector_ignores_nested_consistency_object() -> None:
    from promptbranch_release_state_machine import _select_current_status_result

    payload = {
        "ok": True,
        "action": "artifact_current_all",
        "status": "artifact_registry_loaded",
        "repos": {
            "repo": {
                "ok": True,
                "action": "artifact_current",
                "status": "artifact_registry_loaded",
                "consistency": {
                    "registry_current_matches_state_artifact": True,
                    "state_source_matches_state_artifact": True,
                },
            }
        },
    }
    stdout = json.dumps(payload, indent=2) + "\n"

    selected = _select_current_status_result(stdout)

    assert selected["ok"] is True
    assert selected["match_count"] == 1
    assert selected["result"]["action"] == "artifact_current_all"


def test_acceptance_result_selector_fails_closed_on_ambiguous_top_level_results() -> None:
    from promptbranch_release_state_machine import _select_accept_candidate_result

    one = {"ok": True, "action": "artifact_accept_candidate", "status": "accepted_candidate"}
    stdout = json.dumps(one) + "\n" + json.dumps(one) + "\n"

    selected = _select_accept_candidate_result(stdout)

    assert selected["ok"] is False
    assert selected["failure_code"] == "candidate_acceptance_report_ambiguous"
    assert selected["match_count"] == 2


def test_production_accept_candidate_uses_action_selected_top_level_result(tmp_path: Path, monkeypatch) -> None:
    class Machine:
        attempt_dir = tmp_path / "attempt"
        repo_id = "chatgpt_claudecode_workflow-2"
        config = SimpleNamespace(
            candidate_python=None,
            version=VERSION,
            profile_dir=tmp_path / "profile",
            repo_root=tmp_path / "repo",
        )

    extracted = Machine.attempt_dir / "runtime" / "extracted"
    extracted.mkdir(parents=True)
    Machine.config.repo_root.mkdir(parents=True)
    (extracted / "promptbranch_cli.py").write_text("# fixture\n", encoding="utf-8")
    record = {
        "attempt_id": "fixture-attempt",
        "artifact": {"sha256": "a" * 64},
        "evidence": {"RUNTIME_PREPARED": {"extraction_path": str(extracted), "candidate_python": str(Path(__import__('sys').executable))}},
    }
    acceptance = {
        "ok": True,
        "action": "artifact_accept_candidate",
        "status": "accepted_candidate",
        "artifact_current": {
            "consistency": {
                "registry_current_matches_state_artifact": True,
                "state_source_matches_state_artifact": True,
            }
        },
        "candidate_registry_entry": {"accepted": True},
        "adoption_performed": True,
    }
    stdout = json.dumps(acceptance, indent=2) + "\n"
    monkeypatch.setattr(
        "promptbranch_release_state_machine.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(stdout=stdout, stderr="", returncode=0),
    )

    result = SubprocessReleaseExecutor().accept_candidate(Machine(), record)

    assert result["ok"] is True
    assert result["status"] == "accepted_candidate"
    assert result["result"]["action"] == "artifact_accept_candidate"
    assert result["result_selection"]["match_count"] == 1
    assert "failure_code" not in result
