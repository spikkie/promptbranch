# Repair v0.0.278.4 — Browser profile monitor UX

## Base release

`chatgpt_claudecode_workflow_v0.0.278.3.zip`

## Repair version

`v0.0.278.4`

## Reason

`v0.0.278.2` introduced bounded browser-profile contention and `v0.0.278.3` repaired ask completion detection for the `Use Voice` idle state. The remaining operator-facing defect was that a known browser profile contention condition during `pb src add` was still surfaced as a nested HTTP 423/source-add failure instead of a first-class scheduling result.

This repair keeps the Dijkstra-style single-owner profile invariant and improves CLI ergonomics without adding the full async operation queue.

## Files changed

- `promptbranch_automation/service.py`
  - Added per-request profile-lock wait override support.
  - Added browser profile monitor status reporting.
  - Preserved the single-owner browser profile lock invariant.

- `promptbranch_container_api.py`
  - Added `GET /v1/browser/status`.
  - Added optional `profile_lock_wait_seconds` form field for source-add requests.

- `promptbranch_service_client.py`
  - Added `browser_status()`.
  - Added `profile_lock_wait_seconds` support for `add_project_source()`.

- `promptbranch_cli.py`
  - Added `pb browser status`.
  - Added `pb src add --wait-for-profile`.
  - Added `pb src add --profile-wait-timeout-seconds`.
  - Added equivalent options to legacy `project-source-add`.
  - Promoted source-add `browser_profile_busy` into a top-level operator result instead of a nested HTTP error string.

- `tests/test_cli_parser.py`
  - Added parser coverage for `pb browser status` and source-add wait flags.

- `tests/test_promptbranch_service_client.py`
  - Added service-client coverage for browser status and source-add lock-wait override.

- `tests/test_promptbranch_timeout_classification.py`
  - Added top-level source-add busy payload coverage.

- `tests/test_promptbranch_automation_service.py`
  - Added browser monitor status coverage.
  - Added per-request profile wait override coverage.

- `tests/test_promptbranch_container_api.py`
  - Added API coverage for browser status and source-add lock-wait override.

## Validation performed

Focused validation was run for the modified surface:

```bash
python3 -m py_compile promptbranch_automation/service.py promptbranch_container_api.py promptbranch_service_client.py promptbranch_cli.py
pytest -q \
  tests/test_cli_parser.py \
  tests/test_promptbranch_service_client.py \
  tests/test_promptbranch_timeout_classification.py \
  tests/test_promptbranch_automation_service.py \
  tests/test_promptbranch_container_api.py
```

Result:

```text
112 passed
```

A repository-wide Python compile check was also run before packaging.

## Explicit scope boundary

This repair does **not** implement the full async operation queue.

It intentionally does not add:

- persisted operation IDs;
- queued source-add execution;
- `pb op list/status/wait/cancel`;
- async ask job records;
- crash-recoverable queued mutation replay.

Those are normal-release control-plane changes and should be handled by a later BrowserSessionManager/async-job release.

## No slice or line advancement

This is a repair release only. It does not advance a normal release line, open a new architectural line, or broaden planned scope.
