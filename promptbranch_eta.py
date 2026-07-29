from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
from statistics import median
import tempfile
from typing import Any, Callable, Mapping, Sequence


ETA_HISTORY_SCHEMA = "promptbranch.eta.history"
ETA_HISTORY_SCHEMA_VERSION = "1.0"
DEFAULT_MAX_HISTORY_RECORDS = 2000


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def human_duration(seconds: float | None) -> str:
    if seconds is None:
        return "unknown"
    total = max(0, int(round(float(seconds))))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def canonical_step_name(step: str) -> str:
    text = str(step or "").strip()
    if text in {"full_direct", "full_localhost"}:
        return "full_transport"
    return text


def default_phase_for_step(step: str) -> str:
    text = canonical_step_name(step)
    if "." in text:
        return text.split(".", 1)[0]
    if text == "full_transport":
        return "full_transport"
    if text in {
        "live_profile_preflight",
        "live_project_ensure",
        "ask_live",
        "visual_artifact_roundtrip",
        "release_live",
    }:
        return "external_live"
    if text in {"sandbox_mutation_rollback_gate", "import_smoke", "artifact_guard"}:
        return "local_release_gate"
    return text.split("_", 1)[0] or "unknown"


def _safe_float(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result) or result < 0:
        return None
    return result


def load_eta_history(path: str | Path | None) -> list[dict[str, Any]]:
    if not path:
        return []
    history_path = Path(path).expanduser()
    if not history_path.is_file():
        return []
    try:
        payload = json.loads(history_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    raw_records = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(raw_records, list):
        return []
    records: list[dict[str, Any]] = []
    for raw in raw_records:
        if not isinstance(raw, dict):
            continue
        duration = _safe_float(raw.get("duration_seconds"))
        step = str(raw.get("step") or "").strip()
        transport = str(raw.get("transport") or "").strip()
        if duration is None or not step or not transport:
            continue
        records.append({
            "step": step,
            "step_key": str(raw.get("step_key") or canonical_step_name(step)),
            "phase": str(raw.get("phase") or default_phase_for_step(step)),
            "transport": transport,
            "duration_seconds": duration,
            "outcome": str(raw.get("outcome") or "passed"),
            "recorded_at": str(raw.get("recorded_at") or ""),
        })
    return records


def write_eta_history(
    path: str | Path | None,
    records: Sequence[Mapping[str, Any]],
    *,
    max_records: int = DEFAULT_MAX_HISTORY_RECORDS,
) -> None:
    if not path:
        return
    history_path = Path(path).expanduser()
    history_path.parent.mkdir(parents=True, exist_ok=True)
    bounded = [dict(record) for record in records[-max(1, int(max_records)):]]
    payload = {
        "schema": ETA_HISTORY_SCHEMA,
        "schema_version": ETA_HISTORY_SCHEMA_VERSION,
        "updated_at": utc_now(),
        "records": bounded,
    }
    fd, temp_name = tempfile.mkstemp(prefix=f".{history_path.name}.", suffix=".tmp", dir=str(history_path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temp_name, history_path)
    finally:
        try:
            Path(temp_name).unlink(missing_ok=True)
        except Exception:
            pass


def append_eta_observation(
    path: str | Path | None,
    *,
    step: str,
    transport: str,
    duration_seconds: float,
    outcome: str = "passed",
    phase_resolver: Callable[[str], str] = default_phase_for_step,
    max_records: int = DEFAULT_MAX_HISTORY_RECORDS,
) -> dict[str, Any] | None:
    duration = _safe_float(duration_seconds)
    step_name = str(step or "").strip()
    transport_name = str(transport or "").strip()
    if not path or duration is None or not step_name or not transport_name:
        return None
    records = load_eta_history(path)
    record = {
        "step": step_name,
        "step_key": canonical_step_name(step_name),
        "phase": phase_resolver(step_name),
        "transport": transport_name,
        "duration_seconds": duration,
        "outcome": str(outcome or "passed"),
        "recorded_at": utc_now(),
    }
    records.append(record)
    write_eta_history(path, records, max_records=max_records)
    return record


def _quantile(sorted_values: Sequence[float], fraction: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    position = max(0.0, min(1.0, fraction)) * (len(sorted_values) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return float(sorted_values[lower])
    weight = position - lower
    return float(sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight)


def _distribution(values: Sequence[float], *, widen: float = 1.0) -> tuple[float, float, float]:
    usable = sorted(float(value) for value in values if _safe_float(value) is not None)
    if not usable:
        raise ValueError("duration distribution is empty")
    middle = float(median(usable))
    if len(usable) == 1:
        low = middle * 0.80
        high = middle * 1.30
    else:
        low = _quantile(usable, 0.25)
        high = _quantile(usable, 0.75)
        if high <= low:
            low = middle * 0.85
            high = middle * 1.20
    low = max(0.0, middle - ((middle - low) * widen))
    high = max(middle, middle + ((high - middle) * widen))
    return low, middle, high


def _eligible_records(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    eligible: list[dict[str, Any]] = []
    for raw in records:
        if not isinstance(raw, Mapping):
            continue
        duration = _safe_float(raw.get("duration_seconds"))
        if duration is None or str(raw.get("outcome") or "passed") != "passed":
            continue
        step = str(raw.get("step") or "").strip()
        transport = str(raw.get("transport") or "").strip()
        if not step or not transport:
            continue
        eligible.append({
            "step": step,
            "step_key": str(raw.get("step_key") or canonical_step_name(step)),
            "phase": str(raw.get("phase") or default_phase_for_step(step)),
            "transport": transport,
            "duration_seconds": duration,
        })
    return eligible


def _prediction_for_step(
    step: str,
    *,
    transport: str,
    records: Sequence[Mapping[str, Any]],
    phase_resolver: Callable[[str], str],
) -> dict[str, Any] | None:
    step_key = canonical_step_name(step)
    phase = phase_resolver(step)
    eligible = _eligible_records(records)

    def values_for(*, target_transport: str, by_step: bool) -> list[float]:
        values: list[float] = []
        for record in eligible:
            if record["transport"] != target_transport:
                continue
            if by_step and record["step_key"] != step_key:
                continue
            if not by_step and record["phase"] != phase:
                continue
            values.append(float(record["duration_seconds"]))
        return values

    candidates: list[tuple[str, list[float], float]] = [
        ("same_step_transport_median", values_for(target_transport=transport, by_step=True), 1.0),
    ]
    if transport == "localhost":
        candidates.append(("direct_same_step_eta_prior", values_for(target_transport="direct", by_step=True), 1.20))
    candidates.append(("same_phase_transport_median", values_for(target_transport=transport, by_step=False), 1.35))
    if transport == "localhost":
        candidates.append(("direct_same_phase_eta_prior", values_for(target_transport="direct", by_step=False), 1.55))

    for basis, values, widen in candidates:
        if not values:
            continue
        low, middle, high = _distribution(values, widen=widen)
        return {
            "step": step,
            "step_key": step_key,
            "phase": phase,
            "transport": transport,
            "basis": basis,
            "sample_count": len(values),
            "low_seconds": low,
            "median_seconds": middle,
            "high_seconds": high,
        }
    return None


def estimate_named_step_eta(
    *,
    units: Sequence[str],
    states: Mapping[str, str],
    current: str | None,
    current_elapsed_seconds: float,
    history_records: Sequence[Mapping[str, Any]],
    transport: str,
    known_skipped_units: Sequence[str] = (),
    transport_by_step: Mapping[str, str] | None = None,
    phase_resolver: Callable[[str], str] = default_phase_for_step,
    previous_eta_seconds: float | None = None,
    previous_eta_high_seconds: float | None = None,
    previous_active_steps: Sequence[str] = (),
) -> dict[str, Any]:
    known_skips = {str(unit) for unit in known_skipped_units}
    active_steps = [
        str(unit)
        for unit in units
        if str(unit) not in known_skips
        and str(states.get(str(unit), "pending")) in {"pending", "running"}
    ]
    active_remaining = len(active_steps)
    if not active_steps:
        return {
            "active_remaining": 0,
            "eta_seconds_approx": 0.0,
            "eta_seconds_range": {"low": 0.0, "high": 0.0},
            "eta_approx": human_duration(0.0),
            "eta_range": f"{human_duration(0.0)}..{human_duration(0.0)}",
            "eta_confidence": "high",
            "eta_basis": "complete",
            "predictions": [],
            "unresolved_steps": [],
            "active_steps": [],
        }

    predictions: list[dict[str, Any]] = []
    unresolved: list[str] = []
    total_low = 0.0
    total_middle = 0.0
    total_high = 0.0
    basis_counts: Counter[str] = Counter()
    for step in active_steps:
        step_transport = str((transport_by_step or {}).get(step) or transport)
        prediction = _prediction_for_step(
            step,
            transport=step_transport,
            records=history_records,
            phase_resolver=phase_resolver,
        )
        if prediction is None:
            unresolved.append(step)
            continue
        low = float(prediction["low_seconds"])
        middle = float(prediction["median_seconds"])
        high = float(prediction["high_seconds"])
        if step == current and str(states.get(step)) == "running":
            elapsed = max(0.0, float(current_elapsed_seconds))
            low = max(0.0, low - elapsed)
            middle = max(0.0, middle - elapsed)
            high = max(0.0, high - elapsed)
            if high <= 0.0:
                # A long-running named step must not make the whole ETA claim
                # completion while the step is visibly still active.
                tail = max(5.0, min(float(prediction["median_seconds"]) * 0.25, 60.0))
                low = 0.0
                middle = tail
                high = max(10.0, tail * 2.0)
                prediction["overrun_tail_applied"] = True
            prediction["elapsed_seconds"] = elapsed
            prediction["remaining_low_seconds"] = low
            prediction["remaining_median_seconds"] = middle
            prediction["remaining_high_seconds"] = high
        total_low += low
        total_middle += middle
        total_high += high
        basis_counts[str(prediction["basis"])] += 1
        predictions.append(prediction)

    if unresolved:
        basis = "insufficient_named_step_history"
        if predictions:
            basis = "partial_named_step_history"
        return {
            "active_remaining": active_remaining,
            "eta_seconds_approx": None,
            "eta_seconds_range": {"low": None, "high": None},
            "eta_approx": "unknown",
            "eta_range": "unknown",
            "eta_confidence": "unknown",
            "eta_basis": basis,
            "predictions": predictions,
            "unresolved_steps": unresolved,
            "active_steps": active_steps,
        }

    prior_active = {str(step) for step in previous_active_steps}
    current_active = set(active_steps)
    monotonic_clamped = False
    if previous_eta_seconds is not None and current_active.issubset(prior_active):
        previous_middle = max(0.0, float(previous_eta_seconds))
        previous_high = _safe_float(previous_eta_high_seconds)
        if total_middle > previous_middle:
            total_middle = previous_middle
            monotonic_clamped = True
        if previous_high is not None and total_high > previous_high:
            total_high = previous_high
            monotonic_clamped = True
        elif previous_high is None and total_high > previous_middle * 1.25:
            # Backward-compatible protection for callers that persisted only
            # the previous midpoint before the range became part of state.
            total_high = previous_middle * 1.25
            monotonic_clamped = True
        total_high = max(total_middle, total_high)
        total_low = min(total_low, total_middle, total_high)

    basis_names = sorted(basis_counts)
    eta_basis = "+".join(basis_names) if basis_names else "unknown"
    if monotonic_clamped:
        eta_basis += "+stable_countdown_clamp"

    if basis_names and all(name == "same_step_transport_median" for name in basis_names):
        minimum_samples = min(int(item["sample_count"]) for item in predictions)
        confidence = "high" if minimum_samples >= 3 else "medium"
    elif any("phase" in name for name in basis_names):
        confidence = "low"
    else:
        confidence = "medium"

    return {
        "active_remaining": active_remaining,
        "eta_seconds_approx": round(total_middle, 3),
        "eta_seconds_range": {"low": round(total_low, 3), "high": round(total_high, 3)},
        "eta_approx": human_duration(total_middle),
        "eta_range": f"{human_duration(total_low)}..{human_duration(total_high)}",
        "eta_confidence": confidence,
        "eta_basis": eta_basis,
        "predictions": predictions,
        "unresolved_steps": [],
        "active_steps": active_steps,
        "monotonic_clamped": monotonic_clamped,
    }
