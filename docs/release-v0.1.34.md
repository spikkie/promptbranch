# Release v0.1.34

## Scope

`v0.1.34` continues focused development from `v0.1.33` and makes the full-test/adoption countdown visible one release earlier.

## Change

The read-only full-test countdown now enters the `near_threshold` planning state when the minimum remaining distance to the configured full-test/adoption threshold is four focused releases, not three.

This makes the pre-threshold adoption-planning window visible at the same point where operator guidance starts saying that the threshold is only a few releases away, while still leaving `full_test_recommended_now` false until the configured threshold is actually reached.

## Non-goals

- No adoption behavior change.
- No Project Source mutation change.
- No ZIP import behavior change.
- No full-test execution change.
- No browser automation change.

## Validation intent

The slice is validated by focused countdown/checkpoint/status-guide regression coverage, smoke, docs-status, config, release install/lifecycle plan checks, and ZIP hygiene verification.
