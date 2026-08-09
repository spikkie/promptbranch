from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from promptbranch_release_eta import (
    RELEASE_ETA_HISTORY_SCHEMA,
    RELEASE_ETA_HISTORY_SCHEMA_VERSION,
    append_release_eta_observation,
    build_release_eta_snapshot,
    estimate_release_eta,
    load_release_eta_history,
    sync_release_eta_history_from_attempts,
)


def _obs(step: str, seconds: float, *, profile: str = "full", release_type: str = "normal") -> dict:
    return {
        "observation_id": f"{profile}-{release_type}-{step}-{seconds}",
        "attempt_id": "a",
        "version": "v0.1.125.3.4.2",
        "baseline_version": "v0.1.125.3.4.1",
        "release_type": release_type,
        "profile": profile,
        "phase": {
            "ARTIFACT_BOUND": "artifact",
            "ARTIFACT_VERIFIED": "artifact",
            "CANDIDATE_REGISTERED": "candidate",
            "RUNTIME_PREPARED": "runtime",
            "TESTED_GREEN": "validation",
            "ACCEPTED": "acceptance",
            "ADOPTED_CURRENT": "promotion",
            "FINAL_VERIFIED": "finalization",
        }[step],
        "transport": {
            "ARTIFACT_BOUND": "local_io",
            "ARTIFACT_VERIFIED": "local_cpu",
            "CANDIDATE_REGISTERED": "local_state",
            "RUNTIME_PREPARED": "docker",
            "TESTED_GREEN": "docker_browser",
            "ACCEPTED": "local_control",
            "ADOPTED_CURRENT": "docker_production",
            "FINAL_VERIFIED": "local_control",
        }[step],
        "step": step,
        "duration_seconds": seconds,
        "outcome": "passed",
        "started_at": "2026-08-07T17:00:00Z",
        "finished_at": "2026-08-07T17:01:00Z",
    }


def test_release_eta_history_roundtrip_keeps_profile_phase_transport_and_step(tmp_path: Path) -> None:
    history = tmp_path / "release-eta-history.json"
    result = append_release_eta_observation(
        history,
        attempt_id="attempt-1",
        version="v0.1.126",
        baseline_version="v0.1.125.3.4.2",
        release_type="normal",
        profile="full",
        step="TESTED_GREEN",
        started_at="2026-08-07T17:00:00Z",
        finished_at="2026-08-07T17:10:00Z",
        outcome="passed",
    )
    assert result is not None
    assert result["profile"] == "full"
    assert result["phase"] == "validation"
    assert result["transport"] == "docker_browser"
    assert result["step"] == "TESTED_GREEN"
    assert result["duration_seconds"] == 600.0
    payload = json.loads(history.read_text(encoding="utf-8"))
    assert payload["schema"] == RELEASE_ETA_HISTORY_SCHEMA
    assert payload["schema_version"] == RELEASE_ETA_HISTORY_SCHEMA_VERSION
    assert len(load_release_eta_history(history)) == 1


def test_release_eta_history_deduplicates_same_transition(tmp_path: Path) -> None:
    history = tmp_path / "release-eta-history.json"
    kwargs = dict(
        attempt_id="attempt-1",
        version="v0.1.126",
        baseline_version="v0.1.125.3.4.2",
        release_type="normal",
        profile="full",
        step="RUNTIME_PREPARED",
        started_at="2026-08-07T17:00:00Z",
        finished_at="2026-08-07T17:00:30Z",
        outcome="passed",
    )
    append_release_eta_observation(history, **kwargs)
    append_release_eta_observation(history, **kwargs)
    assert len(load_release_eta_history(history)) == 1


def test_profile_specific_history_drives_candidate_test_prediction() -> None:
    records = [
        _obs("TESTED_GREEN", 900, profile="full"),
        _obs("TESTED_GREEN", 1000, profile="full"),
        _obs("TESTED_GREEN", 1100, profile="full"),
        _obs("TESTED_GREEN", 90, profile="smoke"),
        _obs("TESTED_GREEN", 100, profile="smoke"),
        _obs("TESTED_GREEN", 110, profile="smoke"),
    ]
    full = estimate_release_eta(
        current_state="RUNTIME_PREPARED",
        target_state="FINAL_VERIFIED",
        profile="full",
        release_type="normal",
        history_records=records,
        configured_test_timeout_seconds=3600,
        now=datetime(2026, 8, 7, 17, 0, tzinfo=timezone.utc),
    )
    smoke = estimate_release_eta(
        current_state="RUNTIME_PREPARED",
        target_state="FINAL_VERIFIED",
        profile="smoke",
        release_type="normal",
        history_records=records,
        configured_test_timeout_seconds=3600,
        now=datetime(2026, 8, 7, 17, 0, tzinfo=timezone.utc),
    )
    full_test = next(item for item in full["predictions"] if item["step"] == "TESTED_GREEN")
    smoke_test = next(item for item in smoke["predictions"] if item["step"] == "TESTED_GREEN")
    assert full_test["median_seconds"] == 1000.0
    assert smoke_test["median_seconds"] == 100.0
    assert full_test["evidence_source"] == "persistent_history"
    assert full_test["confidence"] == "high"


def test_expected_finish_is_exposed_with_confidence_and_evidence_source() -> None:
    records = [_obs(step, 10) for step in (
        "ARTIFACT_BOUND", "ARTIFACT_VERIFIED", "CANDIDATE_REGISTERED", "RUNTIME_PREPARED",
        "TESTED_GREEN", "ACCEPTED", "ADOPTED_CURRENT", "FINAL_VERIFIED",
    )]
    result = estimate_release_eta(
        current_state="DECLARED",
        target_state="FINAL_VERIFIED",
        profile="full",
        release_type="normal",
        history_records=records,
        configured_test_timeout_seconds=3600,
        now=datetime(2026, 8, 7, 17, 0, tzinfo=timezone.utc),
    )
    assert result["eta_seconds_approx"] == 80.0
    assert result["expected_finish_at_approx"] == "2026-08-07T17:01:20Z"
    assert result["eta_confidence"] == "medium"
    assert all(item["evidence_source"] == "persistent_history" for item in result["predictions"])


def test_candidate_timeout_risk_is_reported_without_changing_authority() -> None:
    records = [_obs("TESTED_GREEN", 1500), _obs("TESTED_GREEN", 1800), _obs("TESTED_GREEN", 2100)]
    result = estimate_release_eta(
        current_state="RUNTIME_PREPARED",
        target_state="FINAL_VERIFIED",
        profile="full",
        release_type="normal",
        history_records=records,
        configured_test_timeout_seconds=1200,
        now=datetime(2026, 8, 7, 17, 0, tzinfo=timezone.utc),
    )
    diag = result["timeout_risk"]["candidate_test"]
    assert diag["risk"] == "high"
    assert diag["recommended_timeout_seconds"] > 1200
    assert diag["recommendation_is_advisory"] is True
    assert diag["validation_authority_unchanged"] is True


def test_profile_default_timeout_recommendation_is_available_on_first_run() -> None:
    now = datetime(2026, 8, 7, 17, 0, tzinfo=timezone.utc)
    smoke = estimate_release_eta(
        current_state="DECLARED",
        target_state="FINAL_VERIFIED",
        profile="smoke",
        release_type="normal",
        history_records=[],
        configured_test_timeout_seconds=3600,
        now=now,
    )
    full = estimate_release_eta(
        current_state="DECLARED",
        target_state="FINAL_VERIFIED",
        profile="full",
        release_type="normal",
        history_records=[],
        configured_test_timeout_seconds=3600,
        now=now,
    )
    assert full["timeout_risk"]["candidate_test"]["recommended_timeout_seconds"] > smoke["timeout_risk"]["candidate_test"]["recommended_timeout_seconds"]
    assert full["timeout_risk"]["candidate_test"]["prediction"]["basis"] == "profile_default_prior"


def test_outer_wrapper_timeout_risk_can_be_assessed_read_only() -> None:
    result = estimate_release_eta(
        current_state="DECLARED",
        target_state="FINAL_VERIFIED",
        profile="full",
        release_type="normal",
        history_records=[],
        configured_test_timeout_seconds=3600,
        configured_outer_timeout_seconds=300,
        now=datetime(2026, 8, 7, 17, 0, tzinfo=timezone.utc),
    )
    diag = result["timeout_risk"]["outer_wrapper"]
    assert diag["risk"] == "high"
    assert diag["recommended_timeout_seconds"] > 300
    assert diag["validation_authority_unchanged"] is True


def test_sync_from_canonical_attempt_records_is_deduplicated(tmp_path: Path) -> None:
    profile = tmp_path / ".pb_profile"
    attempt_dir = profile / "release_attempts_v2" / "repo" / "v0.1.125.3.4.2" / "abc"
    attempt_dir.mkdir(parents=True)
    attempt = {
        "schema": "promptbranch.release_attempt",
        "attempt_id": "repo:v0.1.125.3.4.2:abc",
        "target_version": "v0.1.125.3.4.2",
        "baseline_version": "v0.1.125.3.4.1",
        "release_type": "repair",
        "request": {"profile": "full"},
        "transitions": [{
            "source_state": "RUNTIME_PREPARED",
            "destination_state": "TESTED_GREEN",
            "status": "completed",
            "started_at": "2026-08-07T17:00:00Z",
            "finished_at": "2026-08-07T17:10:00Z",
        }],
    }
    (attempt_dir / "attempt.json").write_text(json.dumps(attempt), encoding="utf-8")
    history = profile / "release-eta-history.json"
    first = sync_release_eta_history_from_attempts(profile, history)
    second = sync_release_eta_history_from_attempts(profile, history)
    assert first["added_observations"] == 1
    assert second["added_observations"] == 0
    assert len(load_release_eta_history(history)) == 1


def test_snapshot_tracks_active_transition_elapsed_and_expected_finish(tmp_path: Path) -> None:
    history = tmp_path / "release-eta-history.json"
    snapshot = build_release_eta_snapshot(
        attempt_id="attempt-1",
        current_state="RUNTIME_PREPARED",
        target_state="FINAL_VERIFIED",
        profile="full",
        release_type="normal",
        history_path=history,
        configured_test_timeout_seconds=3600,
        active_transition="TESTED_GREEN",
        active_transition_started_at="2026-08-07T17:00:00Z",
        generated_at="2026-08-07T17:05:00Z",
    )
    assert snapshot["active_transition"] == "TESTED_GREEN"
    assert snapshot["active_transition_elapsed_seconds"] == 300.0
    assert snapshot["expected_finish_at_approx"] is not None
    assert snapshot["timeout_risk"]["candidate_test"]["profile"] == "full"


def test_v01261_whole_release_eta_expands_publication_subphases() -> None:
    result = estimate_release_eta(
        current_state="RUNTIME_PREPARED",
        target_state="FINAL_VERIFIED",
        profile="full",
        release_type="repair",
        history_records=[],
        configured_test_timeout_seconds=3600,
        publication_plan={"commit": True, "push": True, "upload_project_source": True},
        active_transition="TESTED_GREEN",
        active_subphase="CANDIDATE_TEST",
        active_subphase_elapsed_seconds=300,
        now=datetime(2026, 8, 8, 8, 0, tzinfo=timezone.utc),
    )
    tested = next(item for item in result["predictions"] if item["step"] == "TESTED_GREEN")
    names = [item["step"] for item in tested["subphase_predictions"]]
    assert names == ["CANDIDATE_TEST", "WORKTREE_MATERIALIZE", "GIT_COMMIT", "GIT_PUSH", "PROJECT_SOURCE_UPLOAD"]
    assert tested["basis"] == "timed_subphases"
    assert result["eta_seconds_approx"] > 0
    assert result["timeout_risk"]["candidate_test"]["prediction"]["step"] == "CANDIDATE_TEST"


def test_v012611_blocked_retryable_snapshot_suppresses_wall_clock_finish_but_keeps_resume_work(tmp_path: Path) -> None:
    history = tmp_path / "release-eta-history.json"
    snapshot = build_release_eta_snapshot(
        attempt_id="attempt-blocked",
        current_state="CANDIDATE_REGISTERED",
        target_state="FINAL_VERIFIED",
        profile="full",
        release_type="repair",
        history_path=history,
        configured_test_timeout_seconds=3600,
        generated_at="2026-08-08T08:41:00Z",
        publication_plan={"commit": True, "push": True, "upload_project_source": True},
        failure_state="BLOCKED_RETRYABLE",
    )
    assert snapshot["status"] == "blocked_retryable"
    assert snapshot["completion_eta_available"] is False
    assert snapshot["blocked_on"] == "RUNTIME_PREPARED"
    assert snapshot["eta_seconds_approx"] is None
    assert snapshot["eta_seconds_range"] == {"low": None, "high": None}
    assert snapshot["expected_finish_at_approx"] is None
    assert snapshot["expected_finish_at_range"] == {"earliest": None, "latest": None}
    assert snapshot["estimated_work_after_resume_seconds_approx"] > 0
    assert snapshot["estimated_work_after_resume_seconds_range"]["high"] > 0
