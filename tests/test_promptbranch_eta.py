from __future__ import annotations

from pathlib import Path

from promptbranch_eta import (
    append_eta_observation,
    estimate_named_step_eta,
    load_eta_history,
)
import promptbranch_test_suite as suite


def record(step: str, duration: float, *, transport: str = "direct", outcome: str = "passed") -> dict:
    return {
        "step": step,
        "transport": transport,
        "duration_seconds": duration,
        "outcome": outcome,
    }


def test_first_run_without_history_is_explicitly_unknown() -> None:
    result = estimate_named_step_eta(
        units=("browser.one", "browser.two"),
        states={"browser.one": "running", "browser.two": "pending"},
        current="browser.one",
        current_elapsed_seconds=5.0,
        history_records=(),
        transport="direct",
    )
    assert result["active_remaining"] == 2
    assert result["eta_approx"] == "unknown"
    assert result["eta_range"] == "unknown"
    assert result["eta_confidence"] == "unknown"
    assert result["eta_basis"] == "insufficient_named_step_history"


def test_same_step_same_transport_uses_median_and_high_confidence() -> None:
    history = [
        record("browser.one", 10),
        record("browser.one", 20),
        record("browser.one", 30),
    ]
    result = estimate_named_step_eta(
        units=("browser.one",),
        states={"browser.one": "running"},
        current="browser.one",
        current_elapsed_seconds=5,
        history_records=history,
        transport="direct",
    )
    assert result["eta_seconds_approx"] == 15.0
    assert result["eta_confidence"] == "high"
    assert result["eta_basis"] == "same_step_transport_median"


def test_phase_fallback_estimates_unseen_named_step() -> None:
    history = [
        record("browser.previous_one", 10),
        record("browser.previous_two", 20),
    ]
    result = estimate_named_step_eta(
        units=("browser.new_step",),
        states={"browser.new_step": "pending"},
        current=None,
        current_elapsed_seconds=0,
        history_records=history,
        transport="direct",
    )
    assert result["eta_seconds_approx"] == 15.0
    assert result["eta_confidence"] == "low"
    assert result["eta_basis"] == "same_phase_transport_median"


def test_known_skips_are_excluded_before_eta_calculation() -> None:
    history = [record("browser.one", 10)]
    result = estimate_named_step_eta(
        units=("browser.one", "validation.duplicate"),
        states={"browser.one": "pending", "validation.duplicate": "pending"},
        current=None,
        current_elapsed_seconds=0,
        history_records=history,
        transport="direct",
        known_skipped_units=("validation.duplicate",),
    )
    assert result["active_remaining"] == 1
    assert result["unresolved_steps"] == []
    assert result["eta_seconds_approx"] == 10.0


def test_long_running_current_step_retains_nonzero_overrun_tail() -> None:
    history = [record("browser.one", 10), record("browser.one", 12), record("browser.one", 14)]
    result = estimate_named_step_eta(
        units=("browser.one",),
        states={"browser.one": "running"},
        current="browser.one",
        current_elapsed_seconds=60,
        history_records=history,
        transport="direct",
    )
    assert result["eta_seconds_approx"] >= 5.0
    assert result["predictions"][0]["overrun_tail_applied"] is True


def test_same_active_plan_countdown_does_not_increase() -> None:
    history = [record("browser.one", 100)]
    first = estimate_named_step_eta(
        units=("browser.one",),
        states={"browser.one": "running"},
        current="browser.one",
        current_elapsed_seconds=20,
        history_records=history,
        transport="direct",
    )
    second = estimate_named_step_eta(
        units=("browser.one",),
        states={"browser.one": "running"},
        current="browser.one",
        current_elapsed_seconds=10,
        history_records=history,
        transport="direct",
        previous_eta_seconds=first["eta_seconds_approx"],
        previous_active_steps=first["active_steps"],
    )
    assert second["eta_seconds_approx"] <= first["eta_seconds_approx"]
    assert second["monotonic_clamped"] is True


def test_shrinking_plan_clamps_range_high_even_when_midpoint_already_decreases() -> None:
    history = [
        record("validation.one", 4),
        record("validation.two", 1000),
    ]
    result = estimate_named_step_eta(
        units=("validation.new",),
        states={"validation.new": "pending"},
        current=None,
        current_elapsed_seconds=0,
        history_records=history,
        transport="direct",
        previous_eta_seconds=12.0,
        previous_eta_high_seconds=15.0,
        previous_active_steps=("validation.new", "validation.finished"),
    )
    assert result["eta_seconds_approx"] <= 12.0
    assert result["eta_seconds_range"]["high"] <= 15.0
    assert result["eta_seconds_range"]["low"] <= result["eta_seconds_approx"]
    assert result["eta_seconds_approx"] <= result["eta_seconds_range"]["high"]
    assert result["monotonic_clamped"] is True
    assert result["eta_basis"].endswith("+stable_countdown_clamp")


def test_expanding_active_plan_may_expand_eta_range() -> None:
    history = [record("browser.one", 10), record("browser.two", 20)]
    result = estimate_named_step_eta(
        units=("browser.one", "browser.two"),
        states={"browser.one": "pending", "browser.two": "pending"},
        current=None,
        current_elapsed_seconds=0,
        history_records=history,
        transport="direct",
        previous_eta_seconds=5.0,
        previous_eta_high_seconds=6.0,
        previous_active_steps=("browser.one",),
    )
    assert result["eta_seconds_approx"] > 5.0
    assert result["eta_seconds_range"]["high"] > 6.0
    assert result["monotonic_clamped"] is False


def test_direct_history_is_eta_only_localhost_prior() -> None:
    history = [record("browser.one", 40, transport="direct")]
    result = estimate_named_step_eta(
        units=("browser.one",),
        states={"browser.one": "pending"},
        current=None,
        current_elapsed_seconds=0,
        history_records=history,
        transport="localhost",
    )
    assert result["eta_seconds_approx"] == 40.0
    assert result["eta_basis"] == "direct_same_step_eta_prior"
    assert result["eta_confidence"] == "medium"


def test_failed_timing_observation_cannot_become_eta_authority() -> None:
    history = [record("browser.one", 1, outcome="failed")]
    result = estimate_named_step_eta(
        units=("browser.one",),
        states={"browser.one": "pending"},
        current=None,
        current_elapsed_seconds=0,
        history_records=history,
        transport="direct",
    )
    assert result["eta_approx"] == "unknown"


def test_history_roundtrip_is_bounded_and_atomic(tmp_path: Path) -> None:
    path = tmp_path / "eta-history.json"
    append_eta_observation(path, step="browser.one", transport="direct", duration_seconds=3.5)
    append_eta_observation(path, step="browser.two", transport="direct", duration_seconds=4.5)
    records = load_eta_history(path)
    assert [item["step"] for item in records] == ["browser.one", "browser.two"]
    assert not list(tmp_path.glob("*.tmp"))


def test_progress_ledger_eta_never_changes_validation_outcome(tmp_path: Path) -> None:
    class Clock:
        value = 0.0

        def __call__(self) -> float:
            return self.value

    clock = Clock()
    history_path = tmp_path / "eta-history.json"
    append_eta_observation(history_path, step="browser.one", transport="direct", duration_seconds=10)
    ledger = suite.TestProgressLedger(
        ("browser.one", "browser.two"),
        enabled=False,
        transport="direct",
        history_path=history_path,
        clock=clock,
    )
    ledger.start("browser.one")
    clock.value = 4.0
    ledger.finish("browser.one", ok=False)
    ledger.skip_pending(reason="fail_fast")
    snapshot = ledger.snapshot()
    assert snapshot["failed_units"] == 1
    assert snapshot["skipped_units"] == 1
    assert ledger.states == {
        "browser.one": "failed",
        "browser.two": "skipped:fail_fast",
    }
