from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
from statistics import median
import tempfile
from typing import Any, Mapping, Sequence


RELEASE_ETA_HISTORY_SCHEMA = "promptbranch.release_eta.history"
RELEASE_ETA_HISTORY_SCHEMA_VERSION = "1.1"
RELEASE_ETA_SNAPSHOT_SCHEMA = "promptbranch.release_eta.snapshot"
RELEASE_ETA_SNAPSHOT_SCHEMA_VERSION = "1.2"
DEFAULT_MAX_RELEASE_ETA_RECORDS = 1000

RELEASE_STEPS: tuple[str, ...] = (
    "ARTIFACT_BOUND",
    "ARTIFACT_VERIFIED",
    "CANDIDATE_REGISTERED",
    "RUNTIME_PREPARED",
    "TESTED_GREEN",
    "ACCEPTED",
    "ADOPTED_CURRENT",
    "FINAL_VERIFIED",
)

STEP_PHASE: dict[str, str] = {
    "ARTIFACT_BOUND": "artifact",
    "ARTIFACT_VERIFIED": "artifact",
    "CANDIDATE_REGISTERED": "candidate",
    "RUNTIME_PREPARED": "runtime",
    "TESTED_GREEN": "validation",
    "ACCEPTED": "acceptance",
    "ADOPTED_CURRENT": "promotion",
    "FINAL_VERIFIED": "finalization",
}

STEP_TRANSPORT: dict[str, str] = {
    "ARTIFACT_BOUND": "local_io",
    "ARTIFACT_VERIFIED": "local_cpu",
    "CANDIDATE_REGISTERED": "local_state",
    "RUNTIME_PREPARED": "docker",
    "TESTED_GREEN": "docker_browser",
    "ACCEPTED": "local_control",
    "ADOPTED_CURRENT": "docker_production",
    "FINAL_VERIFIED": "local_control",
}

RELEASE_SUBPHASES: tuple[str, ...] = (
    "CANDIDATE_TEST",
    "WORKTREE_MATERIALIZE",
    "GIT_COMMIT",
    "GIT_PUSH",
    "PROJECT_SOURCE_UPLOAD",
)
TIMING_STEPS: tuple[str, ...] = RELEASE_STEPS + RELEASE_SUBPHASES

SUBPHASE_PHASE: dict[str, str] = {
    "CANDIDATE_TEST": "validation",
    "WORKTREE_MATERIALIZE": "publication",
    "GIT_COMMIT": "publication",
    "GIT_PUSH": "publication",
    "PROJECT_SOURCE_UPLOAD": "publication",
}
SUBPHASE_TRANSPORT: dict[str, str] = {
    "CANDIDATE_TEST": "docker_browser",
    "WORKTREE_MATERIALIZE": "local_io",
    "GIT_COMMIT": "local_git",
    "GIT_PUSH": "network_git",
    "PROJECT_SOURCE_UPLOAD": "browser_network",
}
TIMING_PHASE: dict[str, str] = {**STEP_PHASE, **SUBPHASE_PHASE}
TIMING_TRANSPORT: dict[str, str] = {**STEP_TRANSPORT, **SUBPHASE_TRANSPORT}
DEFAULT_SUBPHASE_SECONDS: dict[str, float] = {
    "WORKTREE_MATERIALIZE": 12.0,
    "GIT_COMMIT": 180.0,
    "GIT_PUSH": 30.0,
    "PROJECT_SOURCE_UPLOAD": 120.0,
}

# First-run priors are deliberately coarse. Persistent successful observations
# replace them automatically as evidence accumulates.
DEFAULT_STEP_SECONDS: dict[str, float] = {
    "ARTIFACT_BOUND": 2.0,
    "ARTIFACT_VERIFIED": 4.0,
    "CANDIDATE_REGISTERED": 3.0,
    "RUNTIME_PREPARED": 35.0,
    "ACCEPTED": 30.0,
    "ADOPTED_CURRENT": 60.0,
    "FINAL_VERIFIED": 20.0,
}
DEFAULT_TEST_SECONDS: dict[str, float] = {"smoke": 300.0, "full": 1200.0}
PROFILE_TEST_TIMEOUT_FLOOR: dict[str, float] = {"smoke": 600.0, "full": 1800.0}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_time(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _safe_float(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result) or result < 0:
        return None
    return result


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(dict(payload), handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def _observation_id(*, attempt_id: str, step: str, started_at: str, finished_at: str, outcome: str) -> str:
    raw = "\0".join((attempt_id, step, started_at, finished_at, outcome)).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load_release_eta_history(path: str | Path | None) -> list[dict[str, Any]]:
    if not path:
        return []
    history_path = Path(path).expanduser()
    if not history_path.is_file():
        return []
    try:
        payload = json.loads(history_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(payload, dict) or payload.get("schema") != RELEASE_ETA_HISTORY_SCHEMA:
        return []
    if payload.get("schema_version") != RELEASE_ETA_HISTORY_SCHEMA_VERSION:
        return []
    raw_records = payload.get("records")
    if not isinstance(raw_records, list):
        return []
    result: list[dict[str, Any]] = []
    for raw in raw_records:
        if not isinstance(raw, dict):
            continue
        duration = _safe_float(raw.get("duration_seconds"))
        step = str(raw.get("step") or "")
        profile = str(raw.get("profile") or "")
        transport = str(raw.get("transport") or "")
        phase = str(raw.get("phase") or "")
        if duration is None or step not in TIMING_STEPS or profile not in {"smoke", "full"} or not transport or not phase:
            continue
        result.append({**raw, "duration_seconds": duration})
    return result


def write_release_eta_history(
    path: str | Path,
    records: Sequence[Mapping[str, Any]],
    *,
    max_records: int = DEFAULT_MAX_RELEASE_ETA_RECORDS,
) -> None:
    history_path = Path(path).expanduser()
    bounded = [dict(item) for item in records[-max(1, int(max_records)):]]
    _atomic_json(history_path, {
        "schema": RELEASE_ETA_HISTORY_SCHEMA,
        "schema_version": RELEASE_ETA_HISTORY_SCHEMA_VERSION,
        "updated_at": utc_now(),
        "records": bounded,
    })


def append_release_eta_observation(
    path: str | Path,
    *,
    attempt_id: str,
    version: str,
    baseline_version: str,
    release_type: str,
    profile: str,
    step: str,
    started_at: str,
    finished_at: str,
    outcome: str,
    duration_seconds: float | None = None,
) -> dict[str, Any] | None:
    if step not in TIMING_STEPS or profile not in {"smoke", "full"}:
        return None
    duration = _safe_float(duration_seconds)
    if duration is None:
        started = _parse_time(started_at)
        finished = _parse_time(finished_at)
        if started is None or finished is None:
            return None
        duration = max(0.0, (finished - started).total_seconds())
    observation_id = _observation_id(
        attempt_id=str(attempt_id), step=step, started_at=str(started_at), finished_at=str(finished_at), outcome=str(outcome)
    )
    records = load_release_eta_history(path)
    for existing in records:
        if existing.get("observation_id") == observation_id:
            return existing
    record = {
        "observation_id": observation_id,
        "attempt_id": str(attempt_id),
        "version": str(version),
        "baseline_version": str(baseline_version),
        "release_type": str(release_type),
        "profile": profile,
        "phase": TIMING_PHASE[step],
        "transport": TIMING_TRANSPORT[step],
        "step": step,
        "duration_seconds": round(float(duration), 3),
        "outcome": str(outcome),
        "started_at": str(started_at),
        "finished_at": str(finished_at),
        "recorded_at": utc_now(),
    }
    records.append(record)
    write_release_eta_history(path, records)
    return record


def sync_release_eta_history_from_attempts(profile_dir: str | Path, history_path: str | Path) -> dict[str, Any]:
    profile_root = Path(profile_dir).expanduser()
    records = load_release_eta_history(history_path)
    seen = {str(item.get("observation_id") or "") for item in records}
    added = 0
    scanned = 0
    for attempt_path in sorted((profile_root / "release_attempts_v2").glob("*/*/*/attempt.json")):
        try:
            attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(attempt, dict) or attempt.get("schema") != "promptbranch.release_attempt":
            continue
        transitions = attempt.get("transitions") if isinstance(attempt.get("transitions"), list) else []
        request = attempt.get("request") if isinstance(attempt.get("request"), dict) else {}
        profile = str(request.get("profile") or "")
        if profile not in {"smoke", "full"}:
            continue
        scanned += 1
        for transition in transitions:
            if not isinstance(transition, dict) or transition.get("status") != "completed":
                continue
            step = str(transition.get("destination_state") or "")
            if step not in RELEASE_STEPS:
                continue
            started_at = str(transition.get("started_at") or "")
            finished_at = str(transition.get("finished_at") or "")
            observation_id = _observation_id(
                attempt_id=str(attempt.get("attempt_id") or ""),
                step=step,
                started_at=started_at,
                finished_at=finished_at,
                outcome="passed",
            )
            if observation_id in seen:
                continue
            started = _parse_time(started_at)
            finished = _parse_time(finished_at)
            if started is None or finished is None:
                continue
            records.append({
                "observation_id": observation_id,
                "attempt_id": str(attempt.get("attempt_id") or ""),
                "version": str(attempt.get("target_version") or ""),
                "baseline_version": str(attempt.get("baseline_version") or ""),
                "release_type": str(attempt.get("release_type") or ""),
                "profile": profile,
                "phase": STEP_PHASE[step],
                "transport": STEP_TRANSPORT[step],
                "step": step,
                "duration_seconds": round(max(0.0, (finished - started).total_seconds()), 3),
                "outcome": "passed",
                "started_at": started_at,
                "finished_at": finished_at,
                "recorded_at": utc_now(),
                "source": "canonical_attempt_transition",
            })
            seen.add(observation_id)
            added += 1
    if added or not Path(history_path).is_file():
        write_release_eta_history(history_path, records)
    return {"ok": True, "scanned_attempts": scanned, "added_observations": added, "record_count": len(records)}


def _quantile(values: Sequence[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("no values")
    if len(ordered) == 1:
        return float(ordered[0])
    position = max(0.0, min(1.0, fraction)) * (len(ordered) - 1)
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return float(ordered[low])
    weight = position - low
    return float(ordered[low] * (1.0 - weight) + ordered[high] * weight)


def _distribution(values: Sequence[float], *, widen: float = 1.0) -> tuple[float, float, float]:
    ordered = sorted(float(value) for value in values)
    middle = float(median(ordered))
    if len(ordered) == 1:
        low, high = middle * 0.75, middle * 1.35
    else:
        low, high = _quantile(ordered, 0.25), _quantile(ordered, 0.75)
        if high <= low:
            low, high = middle * 0.85, middle * 1.20
    low = max(0.0, middle - ((middle - low) * widen))
    high = max(middle, middle + ((high - middle) * widen))
    return low, middle, high


def _prediction(step: str, *, profile: str, release_type: str, records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    successful = [
        item for item in records
        if item.get("outcome") == "passed" and _safe_float(item.get("duration_seconds")) is not None
    ]
    if step not in TIMING_STEPS:
        raise ValueError(f"unknown ETA timing step: {step}")
    transport = TIMING_TRANSPORT[step]
    phase = TIMING_PHASE[step]

    candidate_sets: list[tuple[str, list[float], float]] = []
    exact = [float(item["duration_seconds"]) for item in successful if item.get("step") == step and item.get("profile") == profile and item.get("transport") == transport and item.get("release_type") == release_type]
    candidate_sets.append(("same_step_profile_transport_release_type", exact, 1.0))
    same_profile = [float(item["duration_seconds"]) for item in successful if item.get("step") == step and item.get("profile") == profile and item.get("transport") == transport]
    candidate_sets.append(("same_step_profile_transport", same_profile, 1.10))
    same_step = [float(item["duration_seconds"]) for item in successful if item.get("step") == step and item.get("transport") == transport]
    candidate_sets.append(("same_step_transport", same_step, 1.25))
    same_phase = [float(item["duration_seconds"]) for item in successful if item.get("phase") == phase and item.get("profile") == profile and item.get("transport") == transport]
    candidate_sets.append(("same_phase_profile_transport", same_phase, 1.40))

    # v0.1.126 transition observations predate timed publication subphases.
    # Canonical successful TESTED_GREEN evidence remains a useful seed only for
    # the candidate-test subphase; publication timings never inherit it.
    if step == "CANDIDATE_TEST":
        legacy_candidate = [float(item["duration_seconds"]) for item in successful if item.get("step") == "TESTED_GREEN" and item.get("profile") == profile and item.get("transport") == "docker_browser"]
        candidate_sets.append(("canonical_tested_green_seed", legacy_candidate, 1.15))

    for basis, values, widen in candidate_sets:
        if not values:
            continue
        low, middle, high = _distribution(values, widen=widen)
        if basis == "same_step_profile_transport_release_type":
            confidence = "high" if len(values) >= 3 else "medium"
        elif basis in {"same_step_profile_transport", "canonical_tested_green_seed"}:
            confidence = "medium"
        else:
            confidence = "low"
        return {
            "step": step,
            "phase": phase,
            "transport": transport,
            "profile": profile,
            "basis": basis,
            "evidence_source": "persistent_history",
            "sample_count": len(values),
            "confidence": confidence,
            "low_seconds": round(low, 3),
            "median_seconds": round(middle, 3),
            "high_seconds": round(high, 3),
        }

    if step in {"TESTED_GREEN", "CANDIDATE_TEST"}:
        middle = DEFAULT_TEST_SECONDS[profile]
        basis = "profile_default_prior"
    elif step in DEFAULT_SUBPHASE_SECONDS:
        middle = DEFAULT_SUBPHASE_SECONDS[step]
        basis = "subphase_default_prior"
    else:
        middle = DEFAULT_STEP_SECONDS[step]
        basis = "step_default_prior"
    return {
        "step": step,
        "phase": phase,
        "transport": transport,
        "profile": profile,
        "basis": basis,
        "evidence_source": "default_prior",
        "sample_count": 0,
        "confidence": "low",
        "low_seconds": round(middle * 0.65, 3),
        "median_seconds": round(middle, 3),
        "high_seconds": round(middle * 1.60, 3),
    }


def _format_finish(moment: datetime | None) -> str | None:
    if moment is None:
        return None
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def estimate_release_eta(
    *,
    current_state: str,
    target_state: str,
    profile: str,
    release_type: str,
    history_records: Sequence[Mapping[str, Any]],
    configured_test_timeout_seconds: float,
    active_transition: str | None = None,
    active_transition_elapsed_seconds: float = 0.0,
    now: datetime | None = None,
    configured_outer_timeout_seconds: float | None = None,
    publication_plan: Mapping[str, Any] | None = None,
    active_subphase: str | None = None,
    active_subphase_elapsed_seconds: float = 0.0,
    completed_subphases: Sequence[str] | None = None,
) -> dict[str, Any]:
    if profile not in {"smoke", "full"}:
        raise ValueError(f"unsupported profile: {profile}")
    now_dt = now or datetime.now(timezone.utc)
    states = ("DECLARED",) + RELEASE_STEPS
    try:
        current_pos = states.index(current_state)
        target_pos = states.index(target_state)
    except ValueError as exc:
        raise ValueError("unknown release state") from exc
    remaining = [] if target_pos < current_pos else list(states[current_pos + 1:target_pos + 1])
    if active_transition and active_transition in RELEASE_STEPS and active_transition not in remaining and current_state != active_transition:
        remaining.insert(0, active_transition)

    plan = dict(publication_plan or {})
    completed = {str(item) for item in (completed_subphases or [])}
    validation_subphases = ["CANDIDATE_TEST"]
    if plan.get("commit"):
        validation_subphases += ["WORKTREE_MATERIALIZE", "GIT_COMMIT"]
    if plan.get("push"):
        validation_subphases += ["GIT_PUSH"]
    if plan.get("upload_project_source"):
        validation_subphases += ["PROJECT_SOURCE_UPLOAD"]

    predictions: list[dict[str, Any]] = []
    total_low = total_mid = total_high = 0.0
    for step in remaining:
        if step == "TESTED_GREEN" and publication_plan is not None:
            components: list[dict[str, Any]] = []
            low = mid = high = 0.0
            for subphase in validation_subphases:
                if subphase in completed:
                    components.append({"step": subphase, "status": "completed", "remaining_low_seconds": 0.0, "remaining_median_seconds": 0.0, "remaining_high_seconds": 0.0})
                    continue
                component = _prediction(subphase, profile=profile, release_type=release_type, records=history_records)
                if subphase == active_subphase:
                    elapsed = max(0.0, float(active_subphase_elapsed_seconds))
                    component["elapsed_seconds"] = round(elapsed, 3)
                    for key, dest in (("low_seconds", "remaining_low_seconds"), ("median_seconds", "remaining_median_seconds"), ("high_seconds", "remaining_high_seconds")):
                        component[dest] = round(max(0.0, float(component[key]) - elapsed), 3)
                    if component["remaining_high_seconds"] <= 0.0:
                        tail = max(10.0, min(float(component["median_seconds"]) * 0.25, 120.0))
                        component["remaining_low_seconds"] = 0.0
                        component["remaining_median_seconds"] = tail
                        component["remaining_high_seconds"] = tail * 2.0
                        component["overrun_tail_applied"] = True
                    c_low, c_mid, c_high = component["remaining_low_seconds"], component["remaining_median_seconds"], component["remaining_high_seconds"]
                else:
                    c_low, c_mid, c_high = component["low_seconds"], component["median_seconds"], component["high_seconds"]
                low += float(c_low); mid += float(c_mid); high += float(c_high)
                components.append(component)
            confidences = [c.get("confidence") for c in components if c.get("status") != "completed"]
            confidence = "low" if "low" in confidences else ("medium" if "medium" in confidences else "high")
            item = {
                "step": "TESTED_GREEN", "phase": "validation_and_publication", "transport": "composite", "profile": profile,
                "basis": "timed_subphases", "evidence_source": "persistent_history_and_priors", "sample_count": sum(int(c.get("sample_count") or 0) for c in components),
                "confidence": confidence, "low_seconds": round(low,3), "median_seconds": round(mid,3), "high_seconds": round(high,3),
                "subphase_predictions": components,
            }
        else:
            item = _prediction(step, profile=profile, release_type=release_type, records=history_records)
            if step == active_transition and active_subphase is None:
                elapsed = max(0.0, float(active_transition_elapsed_seconds))
                item["elapsed_seconds"] = round(elapsed, 3)
                for key, dest in (("low_seconds", "remaining_low_seconds"), ("median_seconds", "remaining_median_seconds"), ("high_seconds", "remaining_high_seconds")):
                    item[dest] = round(max(0.0, float(item[key]) - elapsed), 3)
                if item["remaining_high_seconds"] <= 0.0:
                    tail = max(10.0, min(float(item["median_seconds"]) * 0.25, 120.0))
                    item["remaining_low_seconds"] = 0.0; item["remaining_median_seconds"] = tail; item["remaining_high_seconds"] = tail * 2.0; item["overrun_tail_applied"] = True
                low, mid, high = item["remaining_low_seconds"], item["remaining_median_seconds"], item["remaining_high_seconds"]
            else:
                low, mid, high = item["low_seconds"], item["median_seconds"], item["high_seconds"]
        total_low += float(low); total_mid += float(mid); total_high += float(high)
        predictions.append(item)

    if not remaining:
        confidence, basis = "high", "complete"
    else:
        confidences = [item["confidence"] for item in predictions]
        confidence = "low" if "low" in confidences else ("medium" if "medium" in confidences else "high")
        basis_counts = Counter(item["basis"] for item in predictions)
        basis = "+".join(f"{name}:{count}" for name, count in sorted(basis_counts.items()))

    test_prediction = _prediction("CANDIDATE_TEST" if publication_plan is not None else "TESTED_GREEN", profile=profile, release_type=release_type, records=history_records)
    recommended_test_timeout = max(PROFILE_TEST_TIMEOUT_FLOOR[profile], float(test_prediction["high_seconds"]) * 1.25 + 60.0)
    configured_test = max(0.0, float(configured_test_timeout_seconds))
    test_risk = "high" if configured_test < float(test_prediction["high_seconds"]) else ("elevated" if configured_test < recommended_test_timeout else "low")
    recommended_outer = max(300.0, total_high * 1.25 + 120.0)
    outer_config = _safe_float(configured_outer_timeout_seconds)
    outer_risk = "not_assessed" if outer_config is None else ("high" if outer_config < total_high else ("elevated" if outer_config < recommended_outer else "low"))
    return {
        "remaining_steps": remaining, "remaining_step_count": len(remaining), "eta_seconds_approx": round(total_mid,3),
        "eta_seconds_range": {"low": round(total_low,3), "high": round(total_high,3)},
        "expected_finish_at_approx": _format_finish(now_dt + timedelta(seconds=total_mid)),
        "expected_finish_at_range": {"earliest": _format_finish(now_dt + timedelta(seconds=total_low)), "latest": _format_finish(now_dt + timedelta(seconds=total_high))},
        "eta_confidence": confidence, "eta_basis": basis, "predictions": predictions,
        "publication_plan": plan if publication_plan is not None else None,
        "active_subphase": active_subphase, "completed_subphases": sorted(completed),
        "timeout_risk": {
            "candidate_test": {"profile": profile, "configured_timeout_seconds": configured_test, "recommended_timeout_seconds": round(recommended_test_timeout,3), "risk": test_risk, "prediction": test_prediction, "recommendation_is_advisory": True, "validation_authority_unchanged": True},
            "outer_wrapper": {"configured_timeout_seconds": outer_config, "recommended_timeout_seconds": round(recommended_outer,3), "risk": outer_risk, "recommendation_is_advisory": True, "validation_authority_unchanged": True},
        },
    }


def build_release_eta_snapshot(
    *,
    attempt_id: str,
    current_state: str,
    target_state: str,
    profile: str,
    release_type: str,
    history_path: str | Path,
    configured_test_timeout_seconds: float,
    active_transition: str | None = None,
    active_transition_started_at: str | None = None,
    configured_outer_timeout_seconds: float | None = None,
    generated_at: str | None = None,
    publication_plan: Mapping[str, Any] | None = None,
    active_subphase: str | None = None,
    active_subphase_started_at: str | None = None,
    completed_subphases: Sequence[str] | None = None,
    failure_state: str | None = None,
) -> dict[str, Any]:
    generated_text = generated_at or utc_now()
    now_dt = _parse_time(generated_text) or datetime.now(timezone.utc)
    active_started = _parse_time(active_transition_started_at)
    elapsed = max(0.0, (now_dt - active_started).total_seconds()) if active_started is not None else 0.0
    subphase_started = _parse_time(active_subphase_started_at)
    subphase_elapsed = max(0.0, (now_dt - subphase_started).total_seconds()) if subphase_started is not None else 0.0
    estimate = estimate_release_eta(
        current_state=current_state,
        target_state=target_state,
        profile=profile,
        release_type=release_type,
        history_records=load_release_eta_history(history_path),
        configured_test_timeout_seconds=configured_test_timeout_seconds,
        active_transition=active_transition,
        active_transition_elapsed_seconds=elapsed,
        now=now_dt,
        configured_outer_timeout_seconds=configured_outer_timeout_seconds,
        publication_plan=publication_plan,
        active_subphase=active_subphase,
        active_subphase_elapsed_seconds=subphase_elapsed,
        completed_subphases=completed_subphases,
    )
    snapshot = {
        "schema": RELEASE_ETA_SNAPSHOT_SCHEMA,
        "schema_version": RELEASE_ETA_SNAPSHOT_SCHEMA_VERSION,
        "generated_at": generated_text,
        "attempt_id": attempt_id,
        "current_state": current_state,
        "target_state": target_state,
        "profile": profile,
        "release_type": release_type,
        "failure_state": failure_state,
        "history_path": str(Path(history_path).expanduser()),
        "history_record_count": len(load_release_eta_history(history_path)),
        "active_transition": active_transition,
        "active_transition_started_at": active_transition_started_at,
        "active_transition_elapsed_seconds": round(elapsed, 3),
        "active_subphase": active_subphase,
        "active_subphase_started_at": active_subphase_started_at,
        "active_subphase_elapsed_seconds": round(subphase_elapsed, 3),
        **estimate,
    }
    if failure_state == "BLOCKED_RETRYABLE" and not active_transition:
        snapshot["status"] = "blocked_retryable"
        snapshot["completion_eta_available"] = False
        snapshot["blocked_on"] = (snapshot.get("remaining_steps") or [None])[0]
        snapshot["estimated_work_after_resume_seconds_approx"] = snapshot.get("eta_seconds_approx")
        snapshot["estimated_work_after_resume_seconds_range"] = dict(snapshot.get("eta_seconds_range") or {})
        snapshot["eta_seconds_approx"] = None
        snapshot["eta_seconds_range"] = {"low": None, "high": None}
        snapshot["expected_finish_at_approx"] = None
        snapshot["expected_finish_at_range"] = {"earliest": None, "latest": None}
    else:
        snapshot["status"] = "eta_available"
        snapshot["completion_eta_available"] = True
    return snapshot


def write_release_eta_snapshot(path: str | Path, payload: Mapping[str, Any]) -> None:
    _atomic_json(Path(path).expanduser(), payload)
