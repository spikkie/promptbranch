from __future__ import annotations

import json
import os
import sys
import zipfile
from pathlib import Path

import pytest

from promptbranch_release_state_machine import (
    FAILURE_STATES,
    LEGAL_TRANSITIONS,
    NORMAL_STATES,
    ReleaseStateMachine,
    ReleaseStateMachineConfig,
    ReleaseStateMachineError,
    SubprocessReleaseExecutor,
    build_machine_from_args,
    canonical_state,
    sha256_file,
)


VERSION = "v0.1.126"
BASELINE = "v0.1.125.3.4.2"
REPO_ID = "chatgpt_claudecode_workflow-2"


def _candidate_zip(root: Path, *, version: str = VERSION, suffix: str = "") -> Path:
    path = root / f"{REPO_ID}_{version}.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("VERSION", version + "\n")
        archive.writestr("pyproject.toml", f'[project]\nname = "promptbranch"\nversion = "{version.removeprefix("v")}"\n')
        archive.writestr("promptbranch_version.py", f'PACKAGE_VERSION = "{version.removeprefix("v")}"\n')
        archive.writestr("promptbranch_cli.py", "print('fixture')\n")
        archive.writestr("README.md", "state machine fixture" + suffix + "\n")
        archive.writestr(".promptbranch-release.json", '{"schema":"fixture"}\n')
        archive.writestr(".promptbranch-repo.json", '{"repo_id":"chatgpt_claudecode_workflow-2"}\n')
        archive.writestr("promptbranch_release_state_machine.py", "# fixture state machine\n")
        service_script = "#!/usr/bin/env bash\nset -euo pipefail\nexit 0\n"
        script_info = zipfile.ZipInfo("run_chatgpt_service.sh")
        script_info.external_attr = 0o100755 << 16
        archive.writestr(script_info, service_script)
        container_script = zipfile.ZipInfo("docker/run-chatgpt-service-in-container.sh")
        container_script.external_attr = 0o100755 << 16
        archive.writestr(container_script, service_script)
        archive.writestr("docker-compose.chatgpt-service.yml", "services:\n  chatgpt-service:\n    image: fixture\n")
        archive.writestr("Dockerfile", "FROM scratch\n")
    return path


class FakeExecutor:
    def __init__(self, *, test_ok: bool = True, accept_ok: bool = True, current_ok: bool = True, promotion_ok: bool = True, cleanup_ok: bool = True):
        self.test_ok = test_ok
        self.accept_ok = accept_ok
        self.current_ok = current_ok
        self.promotion_ok = promotion_ok
        self.cleanup_ok = cleanup_ok
        self.production_version = BASELINE.removeprefix("v")
        self.candidate_alive = True
        self.candidate_image_id = "sha256:tested-candidate-image"
        self.calls: list[str] = []
        self.prepared_environment: dict[str, str] = {}

    def prepare_runtime(self, machine: ReleaseStateMachine, record: dict) -> dict:
        self.calls.append("prepare_runtime")
        extraction = machine.attempt_dir / "runtime" / "extracted"
        extraction.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(record["artifact"]["object_path"]) as archive:
            archive.extractall(extraction)
        isolated = {
            "PYTHONPYCACHEPREFIX": str(machine.attempt_dir / "runtime" / "pycache"),
            "PROMPTBRANCH_PROJECT_STATE_HOME": str(machine.attempt_dir / "runtime" / "project-state"),
            "PROMPTBRANCH_PROJECT_CONFIG_HOME": str(machine.attempt_dir / "runtime" / "project-config"),
            "XDG_STATE_HOME": str(machine.attempt_dir / "runtime" / "xdg-state"),
            "XDG_CONFIG_HOME": str(machine.attempt_dir / "runtime" / "xdg-config"),
            "HOME": str(machine.attempt_dir / "runtime" / "home"),
        }
        self.prepared_environment = isolated
        checkpoint_path = machine.attempt_dir / "runtime" / "runtime-checkpoint.json"
        phases = list(SubprocessReleaseExecutor.RUNTIME_PHASES)
        runtime_source_fingerprint = SubprocessReleaseExecutor._source_fingerprint(extraction)
        checkpoint = {
            "attempt_id": record["attempt_id"],
            "artifact_sha256": record["artifact"]["sha256"],
            "source_fingerprint": runtime_source_fingerprint,
            "completed_phases": phases,
            "phase_evidence": {
                "candidate_health_verified": {
                    "health": {"ok": True, "version": VERSION.removeprefix("v")},
                },
                "candidate_identity_verified": {
                    "checks": {
                        "candidate_health_version_exact": True,
                        "candidate_health_ok": True,
                        "candidate_container_present": True,
                        "image_version_label_exact": True,
                        "image_artifact_sha_label_exact": True,
                        "image_source_fingerprint_label_exact": True,
                        "image_attempt_id_label_exact": True,
                        "container_compose_project_exact": True,
                        "accepted_runtime_before_exact": True,
                        "accepted_runtime_after_exact": True,
                        "accepted_runtime_container_unchanged": True,
                        "accepted_runtime_image_unchanged": True,
                        "accepted_runtime_artifact_sha_unchanged": True,
                        "accepted_runtime_unchanged": True,
                        "candidate_port_isolated": True,
                    }
                },
            },
        }
        checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
        accepted = {
            "present": True,
            "container": {"container_id": "accepted-container", "image": f"promptbranch-service:{BASELINE.removeprefix('v')}"},
            "container_count": 1,
            "health": {"ok": True, "version": BASELINE.removeprefix("v")},
            "health_error": None,
            "docker_ps_returncode": 0,
            "image_id": "sha256:accepted-image",
            "image_labels": {
                "promptbranch.version": BASELINE.removeprefix("v"),
                "promptbranch.artifact_sha256": "accepted-artifact-sha",
            },
            "image_inspect_ok": True,
            "image_inspect_error": None,
        }
        return {
            "ok": True,
            "status": "runtime_prepared",
            "candidate_python": sys.executable,
            "candidate_pytest_version": "9.0.2",
            "candidate_pytest_module": pytest.__file__,
            "candidate_package_version": VERSION.removeprefix("v"),
            "candidate_cli_version": VERSION.removeprefix("v"),
            "service_version": VERSION.removeprefix("v"),
            "service_health": {"ok": True, "version": VERSION.removeprefix("v")},
            "candidate_service_base_url": "http://127.0.0.1:18053",
            "candidate_service_port": 18053,
            "candidate_compose_project": "pb-candidate-fixture",
            "candidate_service_image": "promptbranch-candidate:fixture",
            "accepted_runtime_before": accepted,
            "accepted_runtime_after": accepted,
            "runtime_phases": phases,
            "completed_runtime_phases": phases,
            "runtime_checkpoint_path": str(checkpoint_path),
            "runtime_checkpoint": checkpoint,
            "source_fingerprint": runtime_source_fingerprint,
            "extraction_path": str(extraction),
            "isolated_environment": isolated,
        }


    def _http_json(self, url: str) -> tuple[dict, str | None]:
        self.calls.append("candidate_health_probe")
        if self.candidate_alive:
            return {"ok": True, "version": VERSION.removeprefix("v")}, None
        return {}, "ConnectionRefusedError: candidate runtime intentionally retired"

    def run_tests(self, machine: ReleaseStateMachine, record: dict) -> dict:
        self.calls.append("run_tests")
        failed = 0 if self.test_ok else 1
        passed = 52 if self.test_ok else 51
        report = {
            "ok": self.test_ok,
            "schema": "promptbranch.test_suite.report",
            "schema_version": "1.0",
            "action": "test_suite",
            "profile": machine.config.profile,
            "version": machine.config.version,
            "progress": {
                "total_units": 52,
                "completed_units": 52,
                "passed_units": passed,
                "failed_units": failed,
                "skipped_units": 0,
                "states": {"validation.compileall": "passed" if self.test_ok else "failed"},
                "unresolved_steps": [],
            },
        }
        return {
            "ok": self.test_ok,
            "status": "candidate_test_passed" if self.test_ok else "candidate_test_failed",
            "failure_code": None if self.test_ok else "candidate_test_failed",
            "started_at": "2026-08-06T00:00:00Z",
            "finished_at": "2026-08-06T00:00:01Z",
            "profile": machine.config.profile,
            "artifact_sha256": record["artifact"]["sha256"],
            "candidate_python": sys.executable,
            "candidate_pytest_version": pytest.__version__,
            "report_selected": True,
            "report_schema": "promptbranch.test_suite.report",
            "report_schema_version": "1.0",
            "report_sha256": "a" * 64,
            "stdout_sha256": "b" * 64,
            "stderr_sha256": "c" * 64,
            "completed": 52,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
            "failed_group": None if self.test_ok else "compileall",
            "failed_groups": [] if self.test_ok else ["compileall"],
            "failed_steps": [] if self.test_ok else ["validation.compileall"],
            "result": report,
        }

    def accept_candidate(self, machine: ReleaseStateMachine, record: dict) -> dict:
        self.calls.append("accept_candidate")
        if self.accept_ok:
            registry_path = machine.config.profile_dir / "artifact_candidates.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            for item in registry.get("candidates", []):
                if item.get("version") == machine.config.version and item.get("sha256") == record["artifact"]["sha256"]:
                    item["accepted"] = True
                    item["adoption_performed"] = True
                    item["status"] = "accepted_candidate"
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
        return {
            "ok": self.accept_ok,
            "status": "accepted_candidate" if self.accept_ok else "candidate_acceptance_failed",
            "result": {
                "ok": self.accept_ok,
                "status": "accepted_candidate" if self.accept_ok else "candidate_acceptance_failed",
                "artifact_current": {
                    "version": machine.config.version,
                    "sha256": record["artifact"]["sha256"],
                },
            },
        }

    def current_status(self, machine: ReleaseStateMachine, record: dict) -> dict:
        self.calls.append("current_status")
        version = machine.config.version if self.current_ok else BASELINE
        sha = record["artifact"]["sha256"] if self.current_ok else "0" * 64
        filename = str(record["artifact"].get("filename") or "")
        return {
            "ok": self.current_ok,
            "status": "artifact_registry_loaded" if self.current_ok else "artifact_current_mismatch",
            "result": {
                "ok": self.current_ok,
                "action": "artifact_current",
                "status": "artifact_registry_loaded" if self.current_ok else "artifact_current_mismatch",
                "scope": {"kind": "repo", "repo_id": machine.repo_id},
                "runtime": {"version": version},
                "state": {
                    "artifact_ref": filename if self.current_ok else "baseline.zip",
                    "artifact_version": version,
                    "source_ref": filename if self.current_ok else "baseline.zip",
                    "source_version": version,
                },
                "registry_current": {
                    "filename": filename if self.current_ok else "baseline.zip",
                    "version": version,
                    "sha256": sha,
                },
            },
        }

    def authoritative_runtime_status(self, machine: ReleaseStateMachine, record: dict) -> dict:
        self.calls.append("authoritative_runtime_status")
        expected = machine.config.version.removeprefix("v")
        exact = self.production_version == expected
        return {
            "ok": exact,
            "status": "authoritative_runtime_exact" if exact else "authoritative_runtime_mismatch",
            "runtime": {
                "present": True,
                "container_count": 1,
                "container": {"container_id": "production-container", "image": f"promptbranch-service:{self.production_version}"},
                "health": {"ok": True, "version": self.production_version},
            },
            "image_labels": {
                "promptbranch.version": expected if exact else self.production_version,
                "promptbranch.artifact_sha256": record["artifact"]["sha256"] if exact else "old",
                "promptbranch.release_attempt_id": record["attempt_id"] if exact else "old-attempt",
            },
            "checks": {"health_version_exact": exact},
        }

    def promote_authoritative_runtime(self, machine: ReleaseStateMachine, record: dict) -> dict:
        self.calls.append("promote_authoritative_runtime")
        previous = self.production_version
        if not self.promotion_ok:
            return {
                "ok": False,
                "status": "authoritative_runtime_promotion_failed",
                "failure_code": "authoritative_runtime_promotion_failed",
                "error": "simulated promotion failure",
                "previous_runtime": {"health": {"version": previous}},
                "rollback": {"ok": True, "status": "authoritative_runtime_rolled_back"},
            }
        expected = machine.config.version.removeprefix("v")
        recovered = self.production_version == expected
        self.production_version = expected
        return {
            "ok": True,
            "status": "authoritative_runtime_already_promoted" if recovered else "authoritative_runtime_promoted",
            "recovered": recovered,
            "promotion_performed": not recovered,
            "previous_runtime": {"health": {"version": previous}},
            "candidate_image": "promptbranch-candidate:fixture",
            "candidate_image_id": self.candidate_image_id,
            "production_image": f"promptbranch-service:{expected}",
            "production_image_id": self.candidate_image_id,
            "tested_image_identity_exact": True,
        }

    def cleanup_candidate_runtimes(self, machine: ReleaseStateMachine, record: dict) -> dict:
        self.calls.append("cleanup_candidate_runtimes")
        if self.cleanup_ok:
            self.candidate_alive = False
        return {
            "ok": self.cleanup_ok,
            "status": "candidate_runtimes_cleaned" if self.cleanup_ok else "candidate_runtime_cleanup_failed",
            "failure_code": None if self.cleanup_ok else "candidate_runtime_cleanup_failed",
            "inventory_count": 2,
            "removed": [{"project": "pb-candidate-old"}, {"project": "pb-candidate-current"}] if self.cleanup_ok else [],
        }

    def optional_publication(self, machine: ReleaseStateMachine, record: dict) -> dict:
        self.calls.append("optional_publication")
        requested = {
            "commit": machine.config.commit,
            "push": machine.config.push,
            "upload_project_source": machine.config.upload_project_source,
        }
        mutations = [key for key, value in requested.items() if value]
        return {
            "ok": True,
            "status": "completed" if mutations else "not_requested",
            "requested": requested,
            "mutations_performed": mutations,
        }


def _machine(
    tmp_path: Path,
    *,
    until: str = "final-verified",
    adopt: bool = True,
    executor: FakeExecutor | None = None,
    artifact: Path | None = None,
    commit: bool = False,
    push: bool = False,
    upload_project_source: bool = False,
) -> ReleaseStateMachine:
    repo = tmp_path / REPO_ID
    repo.mkdir(exist_ok=True)
    profile = repo / ".pb_profile"
    artifact = artifact or _candidate_zip(tmp_path)
    return build_machine_from_args(
        repo_root=repo,
        profile_dir=profile,
        artifact=artifact,
        version=VERSION,
        baseline_version=BASELINE,
        release_type="repair",
        profile="full",
        test_timeout=3600,
        until=until,
        adopt=adopt,
        commit=commit,
        push=push,
        upload_project_source=upload_project_source,
        executor=executor or FakeExecutor(),
    )


def _record(machine: ReleaseStateMachine) -> dict:
    return json.loads(machine.attempt_path.read_text(encoding="utf-8"))


def test_state_constants_and_legal_transitions_are_complete() -> None:
    assert NORMAL_STATES == (
        "DECLARED",
        "ARTIFACT_BOUND",
        "ARTIFACT_VERIFIED",
        "CANDIDATE_REGISTERED",
        "RUNTIME_PREPARED",
        "TESTED_GREEN",
        "ACCEPTED",
        "ADOPTED_CURRENT",
        "FINAL_VERIFIED",
    )
    assert FAILURE_STATES == ("BLOCKED_RETRYABLE", "FAILED_TERMINAL")
    assert [LEGAL_TRANSITIONS[state] for state in NORMAL_STATES[:-1]] == list(NORMAL_STATES[1:])
    assert LEGAL_TRANSITIONS["FINAL_VERIFIED"] is None


@pytest.mark.parametrize(
    ("alias", "expected"),
    [
        ("declared", "DECLARED"),
        ("artifact-bound", "ARTIFACT_BOUND"),
        ("candidate_registered", "CANDIDATE_REGISTERED"),
        ("tested-green", "TESTED_GREEN"),
        ("accepted", "ACCEPTED"),
        ("complete", "FINAL_VERIFIED"),
    ],
)
def test_state_aliases_are_canonical(alias: str, expected: str) -> None:
    assert canonical_state(alias) == expected


def test_fresh_release_reaches_every_state_and_final_verification(tmp_path: Path) -> None:
    executor = FakeExecutor()
    machine = _machine(tmp_path, executor=executor)
    payload, code = machine.run()
    assert code == 0, payload
    assert payload["ok"] is True
    assert payload["current_state"] == "FINAL_VERIFIED"
    assert payload["lifecycle_complete"] is True
    assert payload["next_transition"] is None
    record = _record(machine)
    assert set(record["evidence"]) == set(NORMAL_STATES)
    assert [item["destination_state"] for item in record["transitions"]] == list(NORMAL_STATES[1:])
    verification, verify_code = machine.verify()
    assert verify_code == 0, verification
    assert verification["ok"] is True
    assert verification["current_state"] == "FINAL_VERIFIED"
    assert all(item["verified"] for item in verification["states"])
    assert verification["failed_invariants"] == []


def test_each_state_is_verifiable_before_future_states_are_reached(tmp_path: Path) -> None:
    executor = FakeExecutor()
    for index, target in enumerate(NORMAL_STATES):
        local = tmp_path / str(index)
        local.mkdir()
        machine = _machine(local, until=target, adopt=True, executor=executor)
        payload, code = machine.run()
        assert code == 0, payload
        assert payload["current_state"] == target
        verification, verify_code = machine.verify()
        assert verify_code == 0, verification
        by_state = {item["state"]: item for item in verification["states"]}
        for prior in NORMAL_STATES[: index + 1]:
            assert by_state[prior]["reached"] is True
            assert by_state[prior]["verified"] is True
        for future in NORMAL_STATES[index + 1 :]:
            assert by_state[future]["reached"] is False
            assert by_state[future]["verified"] is False


def test_repeated_complete_run_is_idempotent_noop(tmp_path: Path) -> None:
    machine = _machine(tmp_path)
    first, first_code = machine.run()
    assert first_code == 0, first
    before = machine.attempt_path.read_bytes()
    second, second_code = machine.run()
    after = machine.attempt_path.read_bytes()
    assert second_code == 0, second
    assert second["status"] == "already_complete"
    assert second["mutation_performed"] is False
    assert second["transitions_executed"] == []
    assert before == after


@pytest.mark.parametrize(
    "destination",
    ["TESTED_GREEN", "ACCEPTED", "ADOPTED_CURRENT", "FINAL_VERIFIED"],
)
def test_illegal_transition_is_rejected_without_mutation(tmp_path: Path, destination: str) -> None:
    machine = _machine(tmp_path, until="declared")
    initial, code = machine.run()
    assert code == 0, initial
    before = machine.attempt_path.read_bytes()
    result, result_code = machine.force_transition_for_test(destination)
    assert result_code == 1
    assert result["status"] == "illegal_transition"
    assert result["failure_code"] == "illegal_transition"
    assert result["current_state"] == "DECLARED"
    assert result["required_next_transition"] == "ARTIFACT_BOUND"
    assert result["mutation_performed"] is False
    assert machine.attempt_path.read_bytes() == before


def test_interruption_after_every_state_resumes_at_exact_next_transition(tmp_path: Path) -> None:
    executor = FakeExecutor()
    machine = _machine(tmp_path, until="declared", executor=executor)
    payload, code = machine.run()
    assert code == 0, payload
    for expected in NORMAL_STATES[1:]:
        machine.config = ReleaseStateMachineConfig(
            **{**machine.config.__dict__, "until": expected}
        ).normalized()
        before_transition_count = len(_record(machine)["transitions"])
        payload, code = machine.run()
        assert code == 0, payload
        assert payload["current_state"] == expected
        record = _record(machine)
        assert len(record["transitions"]) == before_transition_count + 1
        assert record["transitions"][-1]["destination_state"] == expected


def test_artifact_identity_conflict_for_same_version_is_terminal(tmp_path: Path) -> None:
    first_artifact = _candidate_zip(tmp_path, suffix="first")
    first = _machine(tmp_path, until="artifact-bound", artifact=first_artifact)
    payload, code = first.run()
    assert code == 0, payload
    second_root = tmp_path / "other"
    second_root.mkdir()
    second_artifact = _candidate_zip(second_root, suffix="second")
    # Same repo/profile/version, different SHA.
    second = build_machine_from_args(
        repo_root=first.config.repo_root,
        profile_dir=first.config.profile_dir,
        artifact=second_artifact,
        version=VERSION,
        baseline_version=BASELINE,
        until="artifact-bound",
        executor=FakeExecutor(),
    )
    conflict, conflict_code = second.run()
    assert conflict_code == 2
    assert conflict["failure_state"] == "FAILED_TERMINAL"
    assert conflict["failure"]["code"] == "artifact_identity_conflict"
    original = _record(first)
    assert original["artifact"]["sha256"] == sha256_file(first_artifact)


def test_wrong_embedded_version_fails_terminal_before_registration(tmp_path: Path) -> None:
    artifact = _candidate_zip(tmp_path, version="v0.1.125.2")
    renamed = tmp_path / f"{REPO_ID}_{VERSION}.zip"
    artifact.rename(renamed)
    machine = _machine(tmp_path, until="candidate-registered", artifact=renamed)
    payload, code = machine.run()
    assert code == 2
    assert payload["failure_state"] == "FAILED_TERMINAL"
    assert payload["failure"]["code"] == "artifact_version_mismatch"
    registry = machine.config.profile_dir / "artifact_candidates.json"
    assert not registry.exists()


def test_unsafe_zip_path_fails_structural_verification(tmp_path: Path) -> None:
    artifact = tmp_path / f"{REPO_ID}_{VERSION}.zip"
    with zipfile.ZipFile(artifact, "w") as archive:
        archive.writestr("VERSION", VERSION)
        archive.writestr("../escape.txt", "bad")
    machine = _machine(tmp_path, until="artifact-verified", artifact=artifact)
    payload, code = machine.run()
    assert code == 1
    assert payload["failure_state"] == "BLOCKED_RETRYABLE"
    assert payload["current_state"] == "ARTIFACT_BOUND"


def test_missing_candidate_projection_is_reconstructed_from_authoritative_attempt(tmp_path: Path) -> None:
    machine = _machine(tmp_path, until="tested-green")
    payload, code = machine.run()
    assert code == 0, payload
    registry = machine.config.profile_dir / "artifact_candidates.json"
    registry.unlink()
    verification, verify_code = machine.verify(repair_projections=True)
    assert verify_code == 0, verification
    assert verification["projection_repair"]["status"] == "candidate_projection_reconstructed"
    assert verification["mutation_performed"] is True
    restored = json.loads(registry.read_text(encoding="utf-8"))
    assert len(restored["candidates"]) == 1
    assert restored["candidates"][0]["sha256"] == _record(machine)["artifact"]["sha256"]
    assert restored["candidates"][0]["tested"] is True


def test_missing_projection_without_repair_fails_verification(tmp_path: Path) -> None:
    machine = _machine(tmp_path, until="candidate-registered")
    payload, code = machine.run()
    assert code == 0, payload
    (machine.config.profile_dir / "artifact_candidates.json").unlink()
    verification, verify_code = machine.verify(repair_projections=False)
    assert verify_code == 1
    failed = {item["state"]: item for item in verification["failed_invariants"]}
    assert "CANDIDATE_REGISTERED" in failed


def test_conflicting_duplicate_candidate_blocks_verification_and_testing(tmp_path: Path) -> None:
    executor = FakeExecutor()
    machine = _machine(tmp_path, until="candidate-registered", executor=executor)
    payload, code = machine.run()
    assert code == 0, payload
    registry_path = machine.config.profile_dir / "artifact_candidates.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    conflict = dict(registry["candidates"][0])
    conflict["sha256"] = "f" * 64
    conflict["path"] = str(tmp_path / "different.zip")
    registry["candidates"].append(conflict)
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    verification, verify_code = machine.verify()
    assert verify_code == 1
    candidate_state = next(item for item in verification["states"] if item["state"] == "CANDIDATE_REGISTERED")
    assert candidate_state["checks"]["no_conflicting_candidate"] is False
    assert "run_tests" not in executor.calls


def test_failed_candidate_test_blocks_acceptance_and_is_retryable(tmp_path: Path) -> None:
    executor = FakeExecutor(test_ok=False)
    machine = _machine(tmp_path, until="final-verified", executor=executor)
    payload, code = machine.run()
    assert code == 1
    assert payload["failure_state"] == "BLOCKED_RETRYABLE"
    assert payload["failure"]["code"] == "candidate_test_failed"
    assert payload["current_state"] == "RUNTIME_PREPARED"
    assert "accept_candidate" not in executor.calls


def test_successful_test_rerun_resumes_from_runtime_prepared(tmp_path: Path) -> None:
    failing = FakeExecutor(test_ok=False)
    first = _machine(tmp_path, until="tested-green", executor=failing)
    payload, code = first.run()
    assert code == 1
    assert payload["current_state"] == "RUNTIME_PREPARED"
    passing = FakeExecutor(test_ok=True)
    resumed = _machine(tmp_path, until="tested-green", executor=passing, artifact=first.config.artifact)
    result, result_code = resumed.run()
    assert result_code == 0, result
    assert result["current_state"] == "TESTED_GREEN"
    assert [item["destination_state"] for item in _record(resumed)["transitions"]].count("RUNTIME_PREPARED") == 1
    assert passing.calls == ["run_tests", "optional_publication"]


def test_acceptance_requires_explicit_positive_flag(tmp_path: Path) -> None:
    machine = _machine(tmp_path, until="accepted", adopt=False)
    payload, code = machine.run()
    assert code == 1
    assert payload["current_state"] == "TESTED_GREEN"
    assert payload["failure"]["code"] == "adoption_not_authorized"
    assert payload["next_transition"] == "ACCEPTED"


def test_resume_can_add_explicit_adoption_authorization(tmp_path: Path) -> None:
    artifact = _candidate_zip(tmp_path)
    first = _machine(tmp_path, until="accepted", adopt=False, artifact=artifact)
    blocked, blocked_code = first.run()
    assert blocked_code == 1
    resumed = _machine(tmp_path, until="final-verified", adopt=True, artifact=artifact)
    payload, code = resumed.run()
    assert code == 0, payload
    assert payload["current_state"] == "FINAL_VERIFIED"
    assert _record(resumed)["request"]["mutation_policy"]["adopt"] is True


def test_acceptance_guard_failure_does_not_partially_advance(tmp_path: Path) -> None:
    executor = FakeExecutor(accept_ok=False)
    machine = _machine(tmp_path, until="accepted", executor=executor)
    payload, code = machine.run()
    assert code == 1
    assert payload["current_state"] == "TESTED_GREEN"
    assert payload["failure"]["code"] == "candidate_acceptance_failed"
    record = _record(machine)
    assert "ACCEPTED" not in record["evidence"]


def test_adopted_current_mismatch_blocks_final_transition(tmp_path: Path) -> None:
    executor = FakeExecutor(current_ok=False)
    machine = _machine(tmp_path, until="final-verified", executor=executor)
    payload, code = machine.run()
    assert code == 1
    assert payload["current_state"] == "ACCEPTED"
    assert payload["failure"]["code"] == "adopted_current_projection_mismatch"


def test_ambient_state_and_dirty_worktree_do_not_affect_candidate_validation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_STATE_HOME", "/ambient/wrong-state")
    monkeypatch.setenv("PROMPTBRANCH_PROJECT_CONFIG_HOME", "/ambient/wrong-config")
    monkeypatch.setenv("XDG_STATE_HOME", "/ambient/xdg-state")
    monkeypatch.setenv("XDG_CONFIG_HOME", "/ambient/xdg-config")
    executor = FakeExecutor()
    machine = _machine(tmp_path, until="tested-green", executor=executor)
    (machine.config.repo_root / "dirty-untracked.txt").write_text("dirty", encoding="utf-8")
    payload, code = machine.run()
    assert code == 0, payload
    isolated = executor.prepared_environment
    assert isolated["PROMPTBRANCH_PROJECT_STATE_HOME"] != os.environ["PROMPTBRANCH_PROJECT_STATE_HOME"]
    assert isolated["PROMPTBRANCH_PROJECT_CONFIG_HOME"] != os.environ["PROMPTBRANCH_PROJECT_CONFIG_HOME"]
    assert (machine.config.repo_root / "dirty-untracked.txt").read_text(encoding="utf-8") == "dirty"


def test_no_implicit_git_source_or_adoption_mutations(tmp_path: Path) -> None:
    executor = FakeExecutor()
    machine = _machine(tmp_path, until="tested-green", adopt=False, executor=executor)
    payload, code = machine.run()
    assert code == 0, payload
    publication = _record(machine)["optional_publication"]
    assert publication["status"] == "not_requested"
    assert publication["mutations_performed"] == []
    assert "accept_candidate" not in executor.calls


def test_explicit_publication_flags_are_recorded_and_executed_only_when_requested(tmp_path: Path) -> None:
    executor = FakeExecutor()
    machine = _machine(
        tmp_path,
        until="tested-green",
        adopt=False,
        executor=executor,
        commit=True,
        push=True,
        upload_project_source=True,
    )
    payload, code = machine.run()
    assert code == 0, payload
    publication = _record(machine)["optional_publication"]
    assert set(publication["mutations_performed"]) == {"commit", "push", "upload_project_source"}


def test_push_without_commit_is_rejected_before_state_creation(tmp_path: Path) -> None:
    artifact = _candidate_zip(tmp_path)
    repo = tmp_path / REPO_ID
    repo.mkdir()
    with pytest.raises(ReleaseStateMachineError, match="--push requires --commit"):
        build_machine_from_args(
            repo_root=repo,
            profile_dir=repo / ".pb_profile",
            artifact=artifact,
            version=VERSION,
            baseline_version=BASELINE,
            push=True,
        )
    assert not (repo / ".pb_profile" / "release_attempts_v2").exists()


def test_candidate_test_evidence_is_bound_to_exact_sha(tmp_path: Path) -> None:
    machine = _machine(tmp_path, until="tested-green")
    payload, code = machine.run()
    assert code == 0, payload
    record = _record(machine)
    test_path = Path(record["evidence"]["TESTED_GREEN"]["test_record_path"])
    test_record = json.loads(test_path.read_text(encoding="utf-8"))
    assert test_record["result"]["artifact_sha256"] == record["artifact"]["sha256"]
    assert test_record["result"]["profile"] == "full"
    assert test_record["result"]["status"] == "candidate_test_passed"


def test_tampered_test_evidence_is_detected(tmp_path: Path) -> None:
    machine = _machine(tmp_path, until="tested-green")
    payload, code = machine.run()
    assert code == 0, payload
    record = _record(machine)
    test_path = Path(record["evidence"]["TESTED_GREEN"]["test_record_path"])
    test_record = json.loads(test_path.read_text(encoding="utf-8"))
    test_record["result"]["artifact_sha256"] = "0" * 64
    test_path.write_text(json.dumps(test_record), encoding="utf-8")
    verification, verify_code = machine.verify()
    assert verify_code == 1
    tested = next(item for item in verification["states"] if item["state"] == "TESTED_GREEN")
    assert tested["checks"]["test_record_sha_exact"] is False


def test_tampered_artifact_object_is_detected(tmp_path: Path) -> None:
    machine = _machine(tmp_path, until="artifact-verified")
    payload, code = machine.run()
    assert code == 0, payload
    record = _record(machine)
    object_path = Path(record["artifact"]["object_path"])
    object_path.write_bytes(object_path.read_bytes() + b"tamper")
    verification, verify_code = machine.verify()
    assert verify_code == 1
    bound = next(item for item in verification["states"] if item["state"] == "ARTIFACT_BOUND")
    assert bound["checks"]["sha256_exact"] is False


def test_compileall_repeatability_contract_has_isolated_pycache_and_clean_template_projection(tmp_path: Path) -> None:
    machine = _machine(tmp_path, until="runtime-prepared")
    payload, code = machine.run()
    assert code == 0, payload
    runtime = _record(machine)["evidence"]["RUNTIME_PREPARED"]
    isolated = runtime["isolated_environment"]
    assert "PYTHONPYCACHEPREFIX" in isolated
    extraction = Path(runtime["extraction_path"])
    for _ in range(2):
        compile(extraction.joinpath("promptbranch_version.py").read_text(encoding="utf-8"), "promptbranch_version.py", "exec")
    assert not list(extraction.rglob("__pycache__"))
    assert not list(extraction.rglob("*.pyc"))
    assert not list(extraction.rglob("*.pyo"))


def test_final_convergence_assertions_are_all_true(tmp_path: Path) -> None:
    machine = _machine(tmp_path)
    payload, code = machine.run()
    assert code == 0, payload
    record = _record(machine)
    final = record["evidence"]["FINAL_VERIFIED"]
    assert final["guards"] == {
        "all_prior_states_verified": True,
        "failed_invariants_empty": True,
        "candidate_test_passed": True,
        "candidate_accepted": True,
        "accepted_candidate_matches_current": True,
        "authoritative_runtime_exact": True,
    }
    assert record["state"] == "FINAL_VERIFIED"
    assert record["lifecycle_complete"] is True
    assert record["next_transition"] is None


def test_cli_parser_exposes_run_and_verify_commands() -> None:
    from promptbranch_cli import make_parser

    parser = make_parser()
    run = parser.parse_args(
        [
            "release",
            "run",
            "--artifact",
            f"{REPO_ID}_{VERSION}.zip",
            "--version",
            VERSION,
            "--baseline-version",
            BASELINE,
            "--until",
            "accepted",
            "--adopt",
            "--json",
        ]
    )
    assert run.release_command == "run"
    assert run.adopt is True
    assert run.until == "accepted"
    verify = parser.parse_args(["release", "verify", "--version", VERSION, "--all-states", "--json"])
    assert verify.release_command == "verify"
    assert verify.all_states is True


def test_target_version_must_advance_baseline(tmp_path: Path) -> None:
    artifact = _candidate_zip(tmp_path)
    with pytest.raises(ReleaseStateMachineError, match="target version must be newer than baseline"):
        build_machine_from_args(
            repo_root=tmp_path / REPO_ID,
            profile_dir=tmp_path / REPO_ID / ".pb_profile",
            artifact=artifact,
            version=VERSION,
            baseline_version=VERSION,
        )


def test_success_payload_with_required_skip_is_rejected_before_tested_green(tmp_path: Path) -> None:
    class SkipExecutor(FakeExecutor):
        def run_tests(self, machine: ReleaseStateMachine, record: dict) -> dict:
            result = super().run_tests(machine, record)
            result["skipped"] = 1
            result["result"]["progress"]["skipped"] = 1
            return result

    machine = _machine(tmp_path, until="tested-green", executor=SkipExecutor())
    payload, code = machine.run()
    assert code == 1
    assert payload["current_state"] == "RUNTIME_PREPARED"
    assert payload["failure"]["code"] == "candidate_test_evidence_invalid"
    assert payload["failure"]["details"]["guards"]["required_skips_zero"] is False


def test_runtime_evidence_requires_exact_cli_service_and_pytest_versions(tmp_path: Path) -> None:
    machine = _machine(tmp_path, until="runtime-prepared")
    payload, code = machine.run()
    assert code == 0, payload
    record = _record(machine)
    runtime = record["evidence"]["RUNTIME_PREPARED"]
    assert runtime["candidate_package_version"] == VERSION.removeprefix("v")
    assert runtime["candidate_cli_version"] == VERSION.removeprefix("v")
    assert runtime["service_version"] == VERSION.removeprefix("v")
    assert runtime["candidate_pytest_version"] == "9.0.2"
    verification, verify_code = machine.verify()
    assert verify_code == 0, verification
    runtime_state = next(item for item in verification["states"] if item["state"] == "RUNTIME_PREPARED")
    assert runtime_state["checks"]["candidate_cli_version_exact"] is True
    assert runtime_state["checks"]["service_version_exact"] is True
    assert runtime_state["checks"]["pytest_version_exact"] is True


def test_acceptance_resume_recovers_already_adopted_projection_without_repeating_accept(tmp_path: Path) -> None:
    executor = FakeExecutor()
    machine = _machine(tmp_path, until="tested-green", executor=executor)
    payload, code = machine.run()
    assert code == 0, payload
    record = _record(machine)
    registry_path = machine.config.profile_dir / "artifact_candidates.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    for item in registry["candidates"]:
        if item.get("version") == VERSION:
            item["accepted"] = True
            item["adoption_performed"] = True
            item["status"] = "accepted_candidate"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    machine.config = ReleaseStateMachineConfig(**{**machine.config.__dict__, "until": "ACCEPTED"}).normalized()
    before_accept_calls = executor.calls.count("accept_candidate")
    resumed, resumed_code = machine.run()
    assert resumed_code == 0, resumed
    assert resumed["current_state"] == "ACCEPTED"
    assert executor.calls.count("accept_candidate") == before_accept_calls
    accepted = _record(machine)["evidence"]["ACCEPTED"]
    assert accepted["status"] == "accepted_candidate_recovered"
    assert accepted["recovered"] is True



def test_candidate_test_retry_uses_fresh_project_and_persists_attempt_history(tmp_path: Path) -> None:
    executor = FakeExecutor(test_ok=False)
    machine = _machine(tmp_path, until="tested-green", executor=executor)

    first, first_code = machine.run()
    assert first_code == 1
    assert first["current_state"] == "RUNTIME_PREPARED"
    first_record = _record(machine)
    assert len(first_record["test_attempts"]) == 1
    first_attempt = first_record["test_attempts"][0]
    assert first_attempt["retry_number"] == 1
    assert first_attempt["status"] == "failed"
    assert first_attempt["retained_for_forensics"] is True
    assert first_attempt["project_name"].startswith("itest-pb-sm-")

    executor.test_ok = True
    second, second_code = machine.run()
    assert second_code == 0, second
    assert second["current_state"] == "TESTED_GREEN"
    second_record = _record(machine)
    assert len(second_record["test_attempts"]) == 2
    first_attempt, second_attempt = second_record["test_attempts"]
    assert second_attempt["retry_number"] == 2
    assert second_attempt["status"] == "passed"
    assert second_attempt["project_name"] != first_attempt["project_name"]
    assert second_attempt["test_run_id"] != first_attempt["test_run_id"]
    assert first_attempt["superseded_by_test_run_id"] == second_attempt["test_run_id"]
    assert second_attempt["retained_for_forensics"] is False
    assert "active_test_attempt" not in second_record
    tested = second_record["evidence"]["TESTED_GREEN"]
    assert tested["retry_number"] == 2
    assert tested["test_run_id"] == second_attempt["test_run_id"]
    assert tested["project_name"] == second_attempt["project_name"]

def test_release_attempt_schema_declares_every_state_and_failure_classification() -> None:
    schema_path = Path(__file__).resolve().parents[1] / "promptbranch_protocol" / "schemas" / "release.attempt.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["properties"]["schema"]["const"] == "promptbranch.release_attempt"
    assert schema["properties"]["schema_version"]["const"] == "2.0"
    assert tuple(schema["properties"]["state"]["enum"]) == NORMAL_STATES
    assert set(schema["properties"]["failure_state"]["enum"]) == {None, *FAILURE_STATES}


class ScriptedProductionExecutor(SubprocessReleaseExecutor):
    def __init__(self, *, fail_phase: str | None = None, accepted_mode: str = "healthy"):
        self.fail_phase = fail_phase
        self.accepted_mode = accepted_mode
        self.accepted_snapshot_count = 0
        self.logged_calls: list[str] = []
        self.capture_calls: list[list[str]] = []

    def _python(self, machine: ReleaseStateMachine) -> Path:
        return Path(sys.executable)

    def _port_is_free(self, port: int) -> bool:
        return True

    @staticmethod
    def _healthy_accepted_snapshot(*, image_id: str = "sha256:accepted-image", artifact_sha: str = "accepted-artifact-sha") -> dict:
        baseline = BASELINE.removeprefix("v")
        return {
            "present": True,
            "container": {"container_id": "accepted-container", "name": "accepted", "image": f"promptbranch-service:{baseline}", "ports": "0.0.0.0:8000->8000/tcp"},
            "container_count": 1,
            "health": {"ok": True, "version": baseline},
            "health_error": None,
            "docker_ps_returncode": 0,
            "image_id": image_id,
            "image_labels": {
                "promptbranch.version": baseline,
                "promptbranch.artifact_sha256": artifact_sha,
            },
            "image_inspect_ok": True,
            "image_inspect_error": None,
        }

    def _snapshot_accepted_runtime(self, *, cwd: Path, env: dict[str, str]) -> dict:
        self.accepted_snapshot_count += 1
        if self.accepted_mode == "absent":
            return {
                "present": False,
                "container": {},
                "container_count": 0,
                "health": {},
                "health_error": "ConnectionRefusedError",
                "docker_ps_returncode": 0,
                "image_id": None,
                "image_labels": {},
                "image_inspect_ok": False,
                "image_inspect_error": None,
            }
        if self.accepted_mode == "unhealthy":
            payload = self._healthy_accepted_snapshot()
            payload["health"] = {"ok": False, "version": BASELINE.removeprefix("v")}
            payload["health_error"] = "health check failed"
            return payload
        if self.accepted_mode == "baseline-mismatch":
            payload = self._healthy_accepted_snapshot()
            payload["health"] = {"ok": True, "version": "0.1.125.3.4.1"}
            payload["image_labels"]["promptbranch.version"] = "0.1.125.3.4.1"
            return payload
        if self.accepted_mode == "disappear-after-precondition" and self.accepted_snapshot_count >= 2:
            return {
                "present": False,
                "container": {},
                "container_count": 0,
                "health": {},
                "health_error": "ConnectionRefusedError",
                "docker_ps_returncode": 0,
                "image_id": None,
                "image_labels": {},
                "image_inspect_ok": False,
                "image_inspect_error": None,
            }
        if self.accepted_mode == "image-drift-after-precondition" and self.accepted_snapshot_count >= 2:
            return self._healthy_accepted_snapshot(image_id="sha256:drifted-image", artifact_sha="drifted-artifact-sha")
        return self._healthy_accepted_snapshot()

    def _http_json(self, url: str, *, timeout: float = 5.0):
        if url.endswith(":8000/healthz"):
            return {"ok": True, "version": BASELINE.removeprefix("v")}, None
        return {"ok": True, "version": VERSION.removeprefix("v")}, None

    def _run_logged(self, command, *, cwd, env, log_path, timeout, append=False):
        label = "other"
        joined = " ".join(command)
        if "pipx" in joined:
            label = "install"
        elif " build " in f" {joined} ":
            label = "build"
        elif " up " in f" {joined} ":
            label = "start"
        self.logged_calls.append(label)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(joined + "\n", encoding="utf-8")
        failed = self.fail_phase == label
        return {
            "returncode": 1 if failed else 0,
            "timed_out": False,
            "duration_seconds": 0.01,
            "error": None,
            "command": command,
            "log_path": str(log_path),
        }

    def _run_capture(self, command, *, cwd, env, timeout=60.0):
        self.capture_calls.append(list(command))
        joined = " ".join(command)
        version = VERSION.removeprefix("v")
        artifact_sha = env.get("PROMPTBRANCH_ARTIFACT_SHA256", "")
        source_fingerprint = env.get("PROMPTBRANCH_SOURCE_FINGERPRINT", "")
        attempt_id = env.get("PROMPTBRANCH_RELEASE_ATTEMPT_ID", "")
        if "import json,sys,pytest,promptbranch_version" in joined:
            stdout = json.dumps({
                "python": sys.executable,
                "python_prefix": sys.prefix,
                "pytest_version": "9.0.2",
                "pytest_module": pytest.__file__,
                "package_version": version,
            }) + "\n"
        elif joined.endswith("promptbranch_cli.py --version"):
            stdout = f"promptbranch {version}\n"
        elif "docker image inspect" in joined:
            stdout = json.dumps({
                "promptbranch.version": version,
                "promptbranch.artifact_sha256": artifact_sha,
                "promptbranch.source_fingerprint": source_fingerprint,
                "promptbranch.release_attempt_id": attempt_id,
            }) + "\n"
        elif "docker inspect candidate-container" in joined:
            project = env.get("COMPOSE_PROJECT_NAME", "")
            stdout = json.dumps({"com.docker.compose.project": project}) + "\n"
        elif " ps -q chatgpt-service" in f" {joined}":
            stdout = "candidate-container\n"
        elif "docker ps" in joined:
            stdout = "accepted-container|accepted|promptbranch-service:0.1.124|0.0.0.0:8000->8000/tcp\n"
        else:
            stdout = "{}\n"
        return {"returncode": 0, "stdout": stdout, "stderr": "", "command": command}

    def _collect_runtime_diagnostics(self, machine, record, context, *, label):
        target = machine.attempt_dir / "runtime" / "diagnostics" / label / "summary.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {"label": label, "candidate_service_base_url": context["service_base"], "summary_path": str(target)}
        target.write_text(json.dumps(payload), encoding="utf-8")
        return payload


def test_safe_extract_preserves_runtime_script_execute_bits(tmp_path: Path) -> None:
    artifact = _candidate_zip(tmp_path)
    destination = tmp_path / "extract"
    from promptbranch_release_state_machine import _safe_extract

    _safe_extract(artifact, destination)

    assert os.access(destination / "run_chatgpt_service.sh", os.X_OK)
    assert os.access(destination / "docker" / "run-chatgpt-service-in-container.sh", os.X_OK)


def test_production_runtime_uses_isolated_compose_image_port_and_preserves_accepted_runtime(tmp_path: Path) -> None:
    executor = ScriptedProductionExecutor()
    machine = _machine(tmp_path, until="runtime-prepared", executor=executor)

    payload, code = machine.run()

    assert code == 0, payload
    runtime = _record(machine)["evidence"]["RUNTIME_PREPARED"]
    assert runtime["candidate_service_port"] != 8000
    assert runtime["candidate_compose_project"] != "chatgpt_claudecode_workflow"
    assert runtime["candidate_service_image"].startswith("promptbranch-candidate:")
    assert runtime["accepted_runtime_before"]["container"]["container_id"] == "accepted-container"
    assert runtime["accepted_runtime_after"]["container"]["container_id"] == "accepted-container"
    assert runtime["checks"]["accepted_runtime_before_exact"] is True
    assert runtime["checks"]["accepted_runtime_after_exact"] is True
    assert runtime["checks"]["accepted_runtime_unchanged"] is True
    assert runtime["completed_runtime_phases"] == list(SubprocessReleaseExecutor.RUNTIME_PHASES)
    assert executor.logged_calls == ["install", "build", "start"]


def test_runtime_prepare_blocks_when_accepted_runtime_is_absent_before_candidate_mutation(tmp_path: Path) -> None:
    executor = ScriptedProductionExecutor(accepted_mode="absent")
    machine = _machine(tmp_path, until="runtime-prepared", executor=executor)

    payload, code = machine.run()

    assert code == 1
    assert payload["current_state"] == "CANDIDATE_REGISTERED"
    assert payload["failure_state"] == "BLOCKED_RETRYABLE"
    assert payload["failure"]["code"] == "accepted_runtime_unavailable"
    assert executor.logged_calls == []
    checkpoint = json.loads((machine.attempt_dir / "runtime" / "runtime-checkpoint.json").read_text(encoding="utf-8"))
    assert checkpoint["accepted_runtime_before"]["present"] is False
    assert checkpoint["accepted_runtime_before_checks"]["accepted_runtime_present"] is False
    assert checkpoint["last_phase"] == "accepted_runtime_precondition"


def test_runtime_prepare_blocks_when_accepted_runtime_is_unhealthy(tmp_path: Path) -> None:
    executor = ScriptedProductionExecutor(accepted_mode="unhealthy")
    machine = _machine(tmp_path, until="runtime-prepared", executor=executor)

    payload, code = machine.run()

    assert code == 1
    assert payload["failure"]["code"] == "accepted_runtime_unavailable"
    assert executor.logged_calls == []


def test_runtime_prepare_blocks_when_accepted_runtime_does_not_match_baseline(tmp_path: Path) -> None:
    executor = ScriptedProductionExecutor(accepted_mode="baseline-mismatch")
    machine = _machine(tmp_path, until="runtime-prepared", executor=executor)

    payload, code = machine.run()

    assert code == 1
    assert payload["failure"]["code"] == "accepted_runtime_baseline_mismatch"
    assert executor.logged_calls == []


def test_runtime_prepare_blocks_if_accepted_runtime_disappears_during_candidate_preparation(tmp_path: Path) -> None:
    executor = ScriptedProductionExecutor(accepted_mode="disappear-after-precondition")
    machine = _machine(tmp_path, until="runtime-prepared", executor=executor)

    payload, code = machine.run()

    assert code == 1
    assert payload["failure"]["code"] == "runtime_identity_mismatch"
    checkpoint = json.loads((machine.attempt_dir / "runtime" / "runtime-checkpoint.json").read_text(encoding="utf-8"))
    checks = checkpoint["failure"]["details"]["checks"]
    assert checks["accepted_runtime_before_exact"] is True
    assert checks["accepted_runtime_after_exact"] is False
    assert checks["accepted_runtime_unchanged"] is False
    assert executor.logged_calls == ["install", "build", "start"]


def test_runtime_prepare_blocks_if_accepted_runtime_image_identity_drifts(tmp_path: Path) -> None:
    executor = ScriptedProductionExecutor(accepted_mode="image-drift-after-precondition")
    machine = _machine(tmp_path, until="runtime-prepared", executor=executor)

    payload, code = machine.run()

    assert code == 1
    assert payload["failure"]["code"] == "runtime_identity_mismatch"
    checkpoint = json.loads((machine.attempt_dir / "runtime" / "runtime-checkpoint.json").read_text(encoding="utf-8"))
    checks = checkpoint["failure"]["details"]["checks"]
    assert checks["accepted_runtime_before_exact"] is True
    assert checks["accepted_runtime_after_exact"] is True
    assert checks["accepted_runtime_image_unchanged"] is False
    assert checks["accepted_runtime_artifact_sha_unchanged"] is False
    assert checks["accepted_runtime_unchanged"] is False


def test_runtime_prepare_retry_resnapshots_accepted_runtime_after_operator_recovery(tmp_path: Path) -> None:
    executor = ScriptedProductionExecutor(accepted_mode="absent")
    machine = _machine(tmp_path, until="runtime-prepared", executor=executor)

    first, first_code = machine.run()
    assert first_code == 1
    assert first["failure"]["code"] == "accepted_runtime_unavailable"

    executor.accepted_mode = "healthy"
    second, second_code = machine.run()

    assert second_code == 0, second
    assert second["current_state"] == "RUNTIME_PREPARED"
    assert executor.logged_calls == ["install", "build", "start"]
    runtime = _record(machine)["evidence"]["RUNTIME_PREPARED"]
    assert runtime["checks"]["accepted_runtime_before_exact"] is True
    assert runtime["checks"]["accepted_runtime_after_exact"] is True
    assert runtime["checks"]["accepted_runtime_unchanged"] is True


def test_runtime_prepare_failure_persists_phase_checkpoint_and_resume_skips_completed_work(tmp_path: Path) -> None:
    failing = ScriptedProductionExecutor(fail_phase="start")
    first = _machine(tmp_path, until="runtime-prepared", executor=failing)

    payload, code = first.run()

    assert code == 1
    assert payload["current_state"] == "CANDIDATE_REGISTERED"
    assert payload["failure"]["code"] == "runtime_container_start_failed"
    checkpoint_path = first.attempt_dir / "runtime" / "runtime-checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert checkpoint["completed_phases"] == [
        "candidate_extracted",
        "candidate_cli_installed",
        "candidate_image_built",
    ]
    assert checkpoint["failure"]["code"] == "runtime_container_start_failed"

    resumed_executor = ScriptedProductionExecutor()
    resumed = _machine(tmp_path, until="runtime-prepared", executor=resumed_executor, artifact=first.config.artifact)
    result, result_code = resumed.run()

    assert result_code == 0, result
    assert result["current_state"] == "RUNTIME_PREPARED"
    assert resumed_executor.logged_calls == ["start"]
    runtime = _record(resumed)["evidence"]["RUNTIME_PREPARED"]
    assert runtime["completed_runtime_phases"] == list(SubprocessReleaseExecutor.RUNTIME_PHASES)


def test_compose_and_launcher_allow_attempt_specific_project_port_and_image() -> None:
    root = Path(__file__).resolve().parents[1]
    compose = (root / "docker-compose.chatgpt-service.yml").read_text(encoding="utf-8")
    launcher = (root / "run_chatgpt_service.sh").read_text(encoding="utf-8")
    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")

    assert '"${PROMPTBRANCH_SERVICE_PORT:-8000}:8000"' in compose
    assert "PROMPTBRANCH_RELEASE_ATTEMPT_ID" in compose
    assert 'COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-chatgpt_claudecode_workflow}"' in launcher
    assert 'PROMPTBRANCH_SERVICE_PORT="${PROMPTBRANCH_SERVICE_PORT:-8000}"' in launcher
    assert 'docker compose -p "${COMPOSE_PROJECT_NAME}"' in launcher
    assert 'LABEL promptbranch.release_attempt_id="${PROMPTBRANCH_RELEASE_ATTEMPT_ID}"' in dockerfile


def test_successful_transition_evidence_contains_no_failure_code(tmp_path: Path) -> None:
    machine = _machine(tmp_path, until="final-verified", executor=FakeExecutor())

    payload, code = machine.run()

    assert code == 0, payload
    record = _record(machine)
    assert record["state"] == "FINAL_VERIFIED"
    for state, evidence in record["evidence"].items():
        assert "failure_code" not in evidence, state


def test_acceptance_side_effect_reconciles_after_ambiguous_command_result_without_duplicate_accept(tmp_path: Path) -> None:
    class SideEffectThenAmbiguousExecutor(FakeExecutor):
        def accept_candidate(self, machine: ReleaseStateMachine, record: dict) -> dict:
            self.calls.append("accept_candidate")
            registry_path = machine.config.profile_dir / "artifact_candidates.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            for item in registry["candidates"]:
                if item.get("version") == machine.config.version and item.get("sha256") == record["artifact"]["sha256"]:
                    item["accepted"] = True
                    item["adoption_performed"] = True
                    item["status"] = "accepted_candidate"
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            return {
                "ok": False,
                "status": "candidate_acceptance_report_missing",
                "failure_code": "candidate_acceptance_report_missing",
                "returncode": 0,
                "result": {},
            }

    executor = SideEffectThenAmbiguousExecutor()
    machine = _machine(tmp_path, until="final-verified", executor=executor)

    payload, code = machine.run()

    assert code == 0, payload
    assert payload["current_state"] == "FINAL_VERIFIED"
    assert executor.calls.count("accept_candidate") == 1
    accepted = _record(machine)["evidence"]["ACCEPTED"]
    assert accepted["status"] == "accepted_candidate_reconciled"
    assert accepted["recovered_after_acceptance_command"] is True
    assert accepted["effects"]["recovered_after_ambiguous_or_failed_command"] is True
    assert accepted["effects"]["projection_reused"] is True
    assert accepted["effects"]["projection_written_by_state_machine"] is False
    assert accepted["acceptance_command"]["failure_code"] == "candidate_acceptance_report_missing"


def test_stale_tested_green_attempt_with_authoritative_acceptance_resumes_to_final_without_reaccept(tmp_path: Path) -> None:
    executor = FakeExecutor()
    machine = _machine(tmp_path, until="tested-green", executor=executor)
    payload, code = machine.run()
    assert code == 0, payload

    record = _record(machine)
    registry_path = machine.config.profile_dir / "artifact_candidates.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    for item in registry["candidates"]:
        if item.get("version") == VERSION and item.get("sha256") == record["artifact"]["sha256"]:
            item["accepted"] = True
            item["adoption_performed"] = True
            item["status"] = "accepted_candidate"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")

    machine.config = ReleaseStateMachineConfig(**{**machine.config.__dict__, "until": "FINAL_VERIFIED"}).normalized()
    before = executor.calls.count("accept_candidate")
    resumed, resumed_code = machine.run()

    assert resumed_code == 0, resumed
    assert resumed["current_state"] == "FINAL_VERIFIED"
    assert executor.calls.count("accept_candidate") == before
    accepted = _record(machine)["evidence"]["ACCEPTED"]
    assert accepted["status"] == "accepted_candidate_recovered"
    assert accepted["recovered"] is True


def test_adopted_current_promotes_authoritative_runtime_before_final_verified(tmp_path: Path) -> None:
    executor = FakeExecutor()
    machine = _machine(tmp_path, until="final-verified", executor=executor)

    payload, code = machine.run()

    assert code == 0, payload
    assert payload["current_state"] == "FINAL_VERIFIED"
    assert "promote_authoritative_runtime" in executor.calls
    adopted = _record(machine)["evidence"]["ADOPTED_CURRENT"]
    assert adopted["guards"]["authoritative_runtime_exact"] is True
    assert adopted["effects"]["authoritative_runtime_promotion_performed"] is True
    assert adopted["candidate_runtime_cleanup"]["ok"] is True
    assert executor.production_version == VERSION.removeprefix("v")


def test_authoritative_runtime_promotion_failure_blocks_at_accepted_and_rolls_back(tmp_path: Path) -> None:
    executor = FakeExecutor(promotion_ok=False)
    machine = _machine(tmp_path, until="final-verified", executor=executor)

    payload, code = machine.run()

    assert code == 1
    assert payload["current_state"] == "ACCEPTED"
    assert payload["failure"]["code"] == "authoritative_runtime_promotion_failed"
    assert executor.production_version == BASELINE.removeprefix("v")
    assert "FINAL_VERIFIED" not in _record(machine)["evidence"]


def test_candidate_runtime_cleanup_failure_blocks_adopted_current_and_resume_is_idempotent(tmp_path: Path) -> None:
    executor = FakeExecutor(cleanup_ok=False)
    artifact = _candidate_zip(tmp_path)
    first = _machine(tmp_path, until="final-verified", executor=executor, artifact=artifact)

    payload, code = first.run()

    assert code == 1
    assert payload["current_state"] == "ACCEPTED"
    assert payload["failure"]["code"] == "adopted_current_mismatch"
    assert executor.production_version == VERSION.removeprefix("v")
    promotion_calls = executor.calls.count("promote_authoritative_runtime")

    executor.cleanup_ok = True
    resumed = _machine(tmp_path, until="final-verified", executor=executor, artifact=artifact)
    result, result_code = resumed.run()

    assert result_code == 0, result
    assert result["current_state"] == "FINAL_VERIFIED"
    assert executor.calls.count("promote_authoritative_runtime") == promotion_calls + 1
    adopted = _record(resumed)["evidence"]["ADOPTED_CURRENT"]
    assert adopted["promotion"]["status"] == "authoritative_runtime_already_promoted"
    assert adopted["promotion"]["promotion_performed"] is False


def test_release_verify_rejects_final_verified_when_live_authoritative_runtime_drifts(tmp_path: Path) -> None:
    executor = FakeExecutor()
    machine = _machine(tmp_path, until="final-verified", executor=executor)
    payload, code = machine.run()
    assert code == 0, payload

    executor.production_version = BASELINE.removeprefix("v")
    verification, verify_code = machine.verify()

    assert verify_code == 1
    adopted = next(item for item in verification["states"] if item["state"] == "ADOPTED_CURRENT")
    final = next(item for item in verification["states"] if item["state"] == "FINAL_VERIFIED")
    assert adopted["checks"]["authoritative_runtime_exact"] is False
    assert final["checks"]["authoritative_runtime_exact"] is False
    assert verification["lifecycle_complete"] is False


def test_compose_supports_explicit_authoritative_state_and_debug_mounts() -> None:
    root = Path(__file__).resolve().parents[1]
    compose = (root / "docker-compose.chatgpt-service.yml").read_text(encoding="utf-8")
    assert "PROMPTBRANCH_HOST_STATE_PROFILE_DIR" in compose
    assert "PROMPTBRANCH_HOST_DEBUG_ARTIFACT_DIR" in compose


def test_post_adoption_verification_uses_historical_candidate_evidence_after_cleanup(tmp_path: Path) -> None:
    executor = FakeExecutor()
    machine = _machine(tmp_path, until="final-verified", executor=executor)

    payload, code = machine.run()

    assert code == 0, payload
    assert payload["current_state"] == "FINAL_VERIFIED"
    assert executor.candidate_alive is False
    verification, verify_code = machine.verify()
    assert verify_code == 0, verification
    runtime = next(item for item in verification["states"] if item["state"] == "RUNTIME_PREPARED")
    assert runtime["candidate_verification_mode"] == "historical_after_adoption"
    assert "live_candidate_health_exact" not in runtime["checks"]
    assert runtime["checks"]["recorded_candidate_health_exact"] is True
    assert runtime["checks"]["recorded_candidate_identity_exact"] is True
    assert runtime["checks"]["candidate_retired_after_adoption"] is True
    assert runtime["checks"]["tested_image_promoted_exact"] is True
    assert verification["failed_invariants"] == []
    assert verification["lifecycle_complete"] is True


def test_post_adoption_verification_fails_when_immutable_candidate_health_evidence_is_corrupted(tmp_path: Path) -> None:
    executor = FakeExecutor()
    machine = _machine(tmp_path, until="final-verified", executor=executor)
    payload, code = machine.run()
    assert code == 0, payload

    record = _record(machine)
    checkpoint_path = Path(record["evidence"]["RUNTIME_PREPARED"]["runtime_checkpoint_path"])
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint["phase_evidence"]["candidate_health_verified"]["health"]["ok"] = False
    checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")

    verification, verify_code = machine.verify()
    assert verify_code == 1
    runtime = next(item for item in verification["states"] if item["state"] == "RUNTIME_PREPARED")
    assert runtime["candidate_verification_mode"] == "historical_after_adoption"
    assert runtime["checks"]["recorded_candidate_health_exact"] is False
    assert any(
        item["state"] == "RUNTIME_PREPARED" and "recorded_candidate_health_exact" in item["failed_checks"]
        for item in verification["failed_invariants"]
    )


def test_acceptance_requires_canonical_projection_without_legacy_fallback(tmp_path: Path) -> None:
    class ProjectionlessExecutor(FakeExecutor):
        def accept_candidate(self, machine: ReleaseStateMachine, record: dict) -> dict:
            self.calls.append("accept_candidate")
            return {
                "ok": True,
                "status": "accepted_candidate",
                "result": {"ok": True, "status": "accepted_candidate"},
            }

    executor = ProjectionlessExecutor()
    machine = _machine(tmp_path, until="accepted", executor=executor)

    payload, code = machine.run()

    assert code == 1
    assert payload["current_state"] == "TESTED_GREEN"
    assert payload["failure"]["code"] == "accepted_projection_missing_after_acceptance"
    registry = json.loads((machine.config.profile_dir / "artifact_candidates.json").read_text(encoding="utf-8"))
    candidate = next(item for item in registry["candidates"] if item.get("version") == VERSION)
    assert candidate.get("accepted") is not True
    assert candidate.get("adoption_performed") is not True


def test_release_state_machine_persists_whole_release_eta_and_history(tmp_path: Path) -> None:
    machine = _machine(tmp_path, until="runtime-prepared", adopt=True)
    payload, code = machine.run()
    assert code == 0, payload
    assert payload["eta"]["status"] == "eta_available"
    assert payload["eta"]["target_state"] == "FINAL_VERIFIED"
    assert payload["eta"]["expected_finish_at_approx"]
    assert payload["eta"]["timeout_risk"]["candidate_test"]["profile"] == "full"
    assert Path(payload["eta_snapshot_path"]).is_file()
    history_path = machine.config.profile_dir / "release-eta-history.json"
    history = json.loads(history_path.read_text(encoding="utf-8"))
    assert history["schema"] == "promptbranch.release_eta.history"
    completed_steps = {item["step"] for item in history["records"] if item["outcome"] == "passed"}
    assert {"ARTIFACT_BOUND", "ARTIFACT_VERIFIED", "CANDIDATE_REGISTERED", "RUNTIME_PREPARED"}.issubset(completed_steps)


def test_release_eta_status_is_read_only_and_can_assess_outer_timeout(tmp_path: Path) -> None:
    machine = _machine(tmp_path, until="runtime-prepared", adopt=True)
    payload, code = machine.run()
    assert code == 0, payload
    before = machine.attempt_path.read_bytes()
    eta, eta_code = machine.eta_status(configured_outer_timeout_seconds=60)
    after = machine.attempt_path.read_bytes()
    assert eta_code == 0, eta
    assert eta["ok"] is True
    assert eta["mutation_performed"] is False
    assert eta["eta"]["timeout_risk"]["outer_wrapper"]["risk"] in {"high", "elevated", "low"}
    # ETA inspection writes only the dedicated advisory snapshot, not authoritative attempt state.
    assert before == after


def test_eta_calculation_degradation_never_changes_release_validation_authority(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import promptbranch_release_state_machine as rsm

    def broken_eta(**kwargs):
        raise RuntimeError("simulated ETA failure")

    monkeypatch.setattr(rsm, "build_release_eta_snapshot", broken_eta)
    machine = _machine(tmp_path, until="artifact-verified", adopt=True)
    payload, code = machine.run()
    assert code == 0, payload
    assert payload["current_state"] == "ARTIFACT_VERIFIED"
    assert payload["eta"]["status"] == "eta_degraded"
    assert payload["eta"]["validation_authority_unchanged"] is True


def test_v01261_publication_parser_selects_complete_top_level_document_not_nested() -> None:
    from promptbranch_release_state_machine import _select_action_document

    text = json.dumps({
        "ok": True,
        "action": "add",
        "source": {"operation": "add_project_source", "pid": "21"},
    }) + "\n"
    selected = _select_action_document(text, actions=("add",), result_name="project_source", require_status=False)
    assert selected["ok"] is True
    assert selected["match_count"] == 1
    assert selected["result"]["action"] == "add"
    assert selected["result"]["source"]["operation"] == "add_project_source"


def test_v01261_source_fingerprint_covers_full_source_and_ignores_runtime_state(tmp_path: Path) -> None:
    root = tmp_path / "source"
    root.mkdir()
    (root / "VERSION").write_text("v0.1.126.1\n", encoding="utf-8")
    (root / "promptbranch_version.py").write_text('PACKAGE_VERSION = "0.1.126.1"\n', encoding="utf-8")
    (root / "pyproject.toml").write_text('[project]\nname="promptbranch"\nversion="0.1.126.1"\n', encoding="utf-8")
    (root / "module.py").write_text("x = 1\n", encoding="utf-8")
    first = SubprocessReleaseExecutor._source_fingerprint(root)
    (root / "module.py").write_text("x = 2\n", encoding="utf-8")
    second = SubprocessReleaseExecutor._source_fingerprint(root)
    assert first != second
    profile = root / ".pb_profile"
    profile.mkdir()
    (profile / "runtime.json").write_text('{"noise":true}\n', encoding="utf-8")
    assert SubprocessReleaseExecutor._source_fingerprint(root) == second


def test_v01261_materializes_exact_tested_candidate_over_stale_worktree(tmp_path: Path) -> None:
    artifact = _candidate_zip(tmp_path, version="v0.1.126.1")
    source = tmp_path / "clean"
    source.mkdir()
    from promptbranch_release_state_machine import _safe_extract
    _safe_extract(artifact, source)
    repo = tmp_path / "repo"
    repo.mkdir()
    os.system(f"git -C {repo} init -q")
    (repo / "VERSION").write_text("v0.1.125.2\n", encoding="utf-8")
    (repo / "stale.txt").write_text("obsolete\n", encoding="utf-8")
    (repo / ".pb_profile").mkdir()
    (repo / ".pb_profile" / "keep.json").write_text("{}\n", encoding="utf-8")
    config = ReleaseStateMachineConfig(
        repo_root=repo,
        profile_dir=repo / ".pb_profile",
        artifact=artifact,
        version="v0.1.126.1",
        baseline_version=BASELINE,
        release_type="repair",
    )
    machine = ReleaseStateMachine(config, executor=FakeExecutor())
    expected = SubprocessReleaseExecutor._source_fingerprint(source)
    record = {
        "artifact": {"object_path": str(artifact), "sha256": sha256_file(artifact)},
        "evidence": {
            "RUNTIME_PREPARED": {
                "source_fingerprint": expected,
                "runtime_checkpoint": {"source_fingerprint": expected},
            }
        },
    }
    result = SubprocessReleaseExecutor()._materialize_tested_source(machine, record)
    assert result["ok"] is True, result
    assert result["tested_source_fingerprint"] == expected
    assert result["materialized_worktree_fingerprint"] == expected
    assert (repo / "VERSION").read_text(encoding="utf-8").strip() == "v0.1.126.1"
    assert not (repo / "stale.txt").exists()
    assert (repo / ".pb_profile" / "keep.json").is_file()


def test_v01261_retry_reuses_verified_green_candidate_test_after_publication_block(tmp_path: Path) -> None:
    class RetryPublicationExecutor(FakeExecutor):
        def __init__(self) -> None:
            super().__init__()
            self.publication_calls = 0

        def run_tests(self, machine: ReleaseStateMachine, record: dict) -> dict:
            result = super().run_tests(machine, record)
            logs = machine.attempt_dir / "runtime" / "logs"
            logs.mkdir(parents=True, exist_ok=True)
            report = logs / "reuse.report.json"
            stdout = logs / "reuse.stdout.log"
            stderr = logs / "reuse.stderr.log"
            report.write_text(json.dumps(result["result"]), encoding="utf-8")
            stdout.write_text("green\n", encoding="utf-8")
            stderr.write_text("", encoding="utf-8")
            result.update({
                "report_path": str(report),
                "stdout_path": str(stdout),
                "stderr_path": str(stderr),
                "report_sha256": sha256_file(report),
                "stdout_sha256": sha256_file(stdout),
                "stderr_sha256": sha256_file(stderr),
            })
            return result

        def optional_publication(self, machine: ReleaseStateMachine, record: dict) -> dict:
            self.calls.append("optional_publication")
            self.publication_calls += 1
            if self.publication_calls == 1:
                return {"ok": False, "status": "failed", "failure_code": "simulated_publication_failure", "requested": {"commit": True, "push": False, "upload_project_source": False}, "results": []}
            return {"ok": True, "status": "completed", "requested": {"commit": True, "push": False, "upload_project_source": False}, "mutations_performed": ["commit"]}

    executor = RetryPublicationExecutor()
    machine = _machine(tmp_path, until="tested-green", adopt=False, executor=executor, commit=True)
    first, first_code = machine.run()
    assert first_code == 1
    assert first["failure"]["code"] == "optional_publication_failed"
    assert executor.calls.count("run_tests") == 1
    second, second_code = machine.run()
    assert second_code == 0, second
    assert second["current_state"] == "TESTED_GREEN"
    assert executor.calls.count("run_tests") == 1
    evidence = _record(machine)["evidence"]["TESTED_GREEN"]
    assert evidence["effects"]["reused_green_candidate_test"] is True


def test_v012611_shared_source_fingerprint_is_single_authority(tmp_path: Path) -> None:
    from promptbranch_source_fingerprint import source_fingerprint

    root = tmp_path / "source"
    root.mkdir()
    (root / "VERSION").write_text("v0.1.126.1.1\n", encoding="utf-8")
    (root / "promptbranch_version.py").write_text('PACKAGE_VERSION = "0.1.126.1.1"\n', encoding="utf-8")
    (root / "pyproject.toml").write_text('[project]\nname="promptbranch"\nversion="0.1.126.1.1"\n', encoding="utf-8")
    (root / "module.py").write_text("x = 1\n", encoding="utf-8")
    assert SubprocessReleaseExecutor._source_fingerprint(root) == source_fingerprint(root)


def test_v012611_eta_status_is_successful_read_only_inspection_when_release_is_blocked(tmp_path: Path) -> None:
    machine = _machine(tmp_path, until="artifact-verified", adopt=True)
    payload, code = machine.run()
    assert code == 0, payload
    record = json.loads(machine.attempt_path.read_text(encoding="utf-8"))
    record["failure_state"] = "BLOCKED_RETRYABLE"
    record["failure"] = {"code": "simulated_retryable_block"}
    machine.attempt_path.write_text(json.dumps(record), encoding="utf-8")
    before = machine.attempt_path.read_bytes()
    eta, eta_code = machine.eta_status(configured_outer_timeout_seconds=14400)
    after = machine.attempt_path.read_bytes()
    assert eta_code == 0, eta
    assert eta["ok"] is True
    assert eta["status"] == "blocked_retryable"
    assert eta["eta"]["expected_finish_at_approx"] is None
    assert eta["eta"]["estimated_work_after_resume_seconds_approx"] > 0
    assert before == after


def test_v012611_dockerfile_uses_shared_source_fingerprint_authority() -> None:
    dockerfile = (Path(__file__).resolve().parents[1] / "Dockerfile").read_text(encoding="utf-8")
    assert "from promptbranch_source_fingerprint import source_fingerprint" in dockerfile
    assert 'actual_fingerprint = source_fingerprint(Path("/app"))' in dockerfile
    assert "def source_fingerprint()" not in dockerfile


def test_v012611_source_fingerprint_ignores_packaging_transients(tmp_path: Path) -> None:
    from promptbranch_source_fingerprint import source_fingerprint

    root = tmp_path / "source"
    root.mkdir()
    (root / "VERSION").write_text("v0.1.126.1.1\n", encoding="utf-8")
    (root / "module.py").write_text("x = 1\n", encoding="utf-8")
    expected = source_fingerprint(root)
    (root / "promptbranch.egg-info").mkdir()
    (root / "promptbranch.egg-info" / "PKG-INFO").write_text("generated\n", encoding="utf-8")
    (root / "build").mkdir()
    (root / "build" / "generated.txt").write_text("generated\n", encoding="utf-8")
    assert source_fingerprint(root) == expected


def test_v012611111_runtime_source_fingerprint_checkpoint_is_authoritative(tmp_path: Path) -> None:
    artifact = _candidate_zip(tmp_path, version="v0.1.126.1.1.1.1.1")
    repo = tmp_path / "repo"
    repo.mkdir()
    profile = repo / ".pb_profile"
    config = ReleaseStateMachineConfig(
        repo_root=repo,
        profile_dir=profile,
        artifact=artifact,
        version="v0.1.126.1.1.1.1.1",
        baseline_version=BASELINE,
        release_type="repair",
    )
    machine = ReleaseStateMachine(config, executor=FakeExecutor())
    expected = "a" * 64
    record = {
        "evidence": {
            "RUNTIME_PREPARED": {
                "source_fingerprint": expected,
                "runtime_checkpoint": {"source_fingerprint": expected},
            }
        }
    }
    result = SubprocessReleaseExecutor()._runtime_source_fingerprint(machine, record)
    assert result["ok"] is True
    assert result["authority"] == "runtime_checkpoint"
    assert result["source_fingerprint"] == expected


def test_v012611111_runtime_source_fingerprint_missing_projection_fails_closed(tmp_path: Path) -> None:
    artifact = _candidate_zip(tmp_path, version="v0.1.126.1.1.1.1.1")
    repo = tmp_path / "repo"
    repo.mkdir()
    config = ReleaseStateMachineConfig(
        repo_root=repo,
        profile_dir=repo / ".pb_profile",
        artifact=artifact,
        version="v0.1.126.1.1.1.1.1",
        baseline_version=BASELINE,
        release_type="repair",
    )
    machine = ReleaseStateMachine(config, executor=FakeExecutor())
    expected = "b" * 64
    record = {"evidence": {"RUNTIME_PREPARED": {"runtime_checkpoint": {"source_fingerprint": expected}}}}
    result = SubprocessReleaseExecutor()._runtime_source_fingerprint(machine, record)
    assert result["ok"] is False
    assert result["failure_code"] == "runtime_source_fingerprint_missing"
    assert result["checkpoint_source_fingerprint"] == expected
    assert result["projected_source_fingerprint"] == ""


def test_v012611111_runtime_source_fingerprint_disagreement_fails_closed(tmp_path: Path) -> None:
    artifact = _candidate_zip(tmp_path, version="v0.1.126.1.1.1.1.1")
    repo = tmp_path / "repo"
    repo.mkdir()
    config = ReleaseStateMachineConfig(
        repo_root=repo,
        profile_dir=repo / ".pb_profile",
        artifact=artifact,
        version="v0.1.126.1.1.1.1.1",
        baseline_version=BASELINE,
        release_type="repair",
    )
    machine = ReleaseStateMachine(config, executor=FakeExecutor())
    record = {
        "evidence": {
            "RUNTIME_PREPARED": {
                "source_fingerprint": "c" * 64,
                "runtime_checkpoint": {"source_fingerprint": "d" * 64},
            }
        }
    }
    result = SubprocessReleaseExecutor()._runtime_source_fingerprint(machine, record)
    assert result["ok"] is False
    assert result["failure_code"] == "runtime_source_fingerprint_disagreement"
    assert result["checkpoint_source_fingerprint"] == "d" * 64
    assert result["projected_source_fingerprint"] == "c" * 64


def test_v012611111_publication_materializes_then_reaches_git_commit_with_same_fingerprint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    version = "v0.1.126.1.1.1.1.1"
    artifact = _candidate_zip(tmp_path, version=version)
    clean = tmp_path / "clean"
    clean.mkdir()
    from promptbranch_release_state_machine import _safe_extract
    _safe_extract(artifact, clean)
    expected = SubprocessReleaseExecutor._source_fingerprint(clean)

    repo = tmp_path / "repo"
    repo.mkdir()
    os.system(f"git -C {repo} init -q")
    (repo / "VERSION").write_text("v0.1.125.2\n", encoding="utf-8")
    (repo / "stale.txt").write_text("stale\n", encoding="utf-8")
    (repo / ".pb_profile").mkdir()

    config = ReleaseStateMachineConfig(
        repo_root=repo,
        profile_dir=repo / ".pb_profile",
        artifact=artifact,
        version=version,
        baseline_version=BASELINE,
        release_type="repair",
        commit=True,
        push=False,
        upload_project_source=False,
    )
    machine = ReleaseStateMachine(config, executor=FakeExecutor())
    record = {
        "attempt_id": machine.attempt_id,
        "artifact": {"object_path": str(artifact), "sha256": sha256_file(artifact)},
        "evidence": {
            "RUNTIME_PREPARED": {
                "source_fingerprint": expected,
                "runtime_checkpoint": {"source_fingerprint": expected},
                "extraction_path": str(clean),
                "candidate_python": sys.executable,
            }
        },
    }
    executor = SubprocessReleaseExecutor()
    calls: list[str] = []

    def fake_publication_command(*args, **kwargs):
        calls.append(kwargs["kind"])
        return {
            "ok": True,
            "result": {
                "ok": True,
                "status": "release_pipeline_applied",
                "version": version,
                "artifact": {"sha256": record["artifact"]["sha256"]},
                "evidence_binding": {"git_commit": "abc123"},
            },
        }

    monkeypatch.setattr(executor, "_run_publication_command", fake_publication_command)
    monkeypatch.setattr(executor, "_git_head_source_fingerprint", lambda machine: {"ok": True, "fingerprint": expected})
    result = executor.optional_publication(machine, record)
    assert result["ok"] is True, result
    assert calls == ["GIT_COMMIT"]
    assert result["mutations_performed"] == ["worktree_materialize", "commit"]
    materialized = next(item for item in result["results"] if item.get("kind") == "worktree_materialize")
    assert materialized["tested_source_fingerprint"] == expected
    git_commit = next(item for item in result["results"] if item.get("kind") == "git_commit")
    assert git_commit["runtime_source_fingerprint"]["source_fingerprint"] == expected
    assert git_commit["guards"]["materialized_worktree_fingerprint_exact"] is True
    assert git_commit["guards"]["committed_tree_fingerprint_exact"] is True


def test_v012611111_prepare_runtime_projects_checkpoint_source_fingerprint_source_contract() -> None:
    source = Path(__file__).resolve().parents[1] / "promptbranch_release_state_machine.py"
    text = source.read_text(encoding="utf-8")
    assert '"source_fingerprint": str(checkpoint.get("source_fingerprint") or "")' in text
    assert 'expected_fingerprint = str(runtime.get("source_fingerprint") or "")' not in text
    assert 'expected_fp = str(runtime.get("source_fingerprint") or "")' not in text
