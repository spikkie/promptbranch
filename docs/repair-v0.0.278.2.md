# Repair v0.0.278.2 — Browser Lock-Wait and Service Timeout Classification

## Base release

v0.0.278.1

## Repair version

v0.0.278.2

## Reason

The v0.0.278.1 repair correctly serialized shared browser-profile access, but lock waiting remained unbounded from the CLI caller's perspective. During a live contention test, both the active `pb ask` and a queued `pb src list` reached the client-side HTTP read timeout and surfaced raw `httpx.ReadTimeout` tracebacks.

This repair keeps the browser profile global-lock behavior but adds explicit, bounded timeout classification so queued browser-backed operations fail cleanly as `browser_profile_busy` before the outer HTTP client times out. It also classifies long service-client read timeouts as `service_client_read_timeout` instead of exposing raw tracebacks.

## Files changed

- `promptbranch_automation/service.py`
  - adds bounded profile-lock acquisition
  - tracks the active browser operation per profile
  - raises `BrowserProfileBusyError` when another operation owns the profile longer than the wait budget
- `promptbranch_browser_auth/exceptions.py`
  - adds `BrowserProfileBusyError` with machine-readable payload support
- `promptbranch_container_api.py`
  - maps `BrowserProfileBusyError` to HTTP 423 with structured detail
  - adds `PROMPTBRANCH_BROWSER_PROFILE_LOCK_WAIT_SECONDS` / `CHATGPT_BROWSER_PROFILE_LOCK_WAIT_SECONDS` configuration
- `promptbranch_cli.py`
  - classifies HTTP 423 `browser_profile_busy` responses
  - classifies service-client `ReadTimeout` / `TimeoutException` as `service_client_read_timeout`
  - emits JSON for `--json` commands and concise non-traceback diagnostics otherwise
- `tests/test_promptbranch_automation_service.py`
  - adds profile contention regression coverage
- `tests/test_promptbranch_timeout_classification.py`
  - adds CLI/service timeout-classification tests
- `VERSION`, `pyproject.toml`, `promptbranch_version.py`
  - updates repair version metadata

## Validation performed

- Python compilation across repository Python files
- Focused pytest:
  - `tests/test_promptbranch_automation_service.py::test_profile_scoped_lock_serializes_services_sharing_profile`
  - `tests/test_promptbranch_automation_service.py::test_profile_scoped_lock_reports_busy_before_client_timeout`
  - `tests/test_promptbranch_timeout_classification.py`
- ZIP reopened and hygiene checked

## Slice / line advancement

No slice or line was advanced. This is a repair-only release that fixes timeout classification and lock-wait behavior in the intended v0.0.278.1 browser-profile safety repair.
