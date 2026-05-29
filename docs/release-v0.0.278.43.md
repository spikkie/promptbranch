# Release v0.0.278.43

## Purpose

Slim the trusted-refill retry fill path after the raw Enter submit attempt has already failed closed as prepare-only.

## Base

Built from `chatgpt_claudecode_workflow_v0.0.278.42.zip`.

## Changes

- Preserve the v0.0.278.42 submit order:
  - raw Enter primary;
  - trusted-refill + Enter retry second.
- Preserve exact-sentinel submit causality gates.
- Preserve fast latest-turn answer promotion.
- Add a slim trusted-refill retry fill mode for `keyboard_enter_refill_retry`:
  - skips rate-limit modal probing during the retry composer focus click;
  - uses a shorter composer focus click timeout;
  - skips full submit/stop/idle button probing during retry prompt verification;
  - verifies only the current prompt marker/prefix in the already resolved composer.
- Add diagnostics:
  - `trusted_refill_retry_slim_fill_used`;
  - `fill_evidence.slim_retry`;
  - `fill_evidence.slim_retry_marker_verify_used`.

## Validation

- `python3 -m compileall -q .`
- Focused test suite:
  - `tests/test_project_list_browser_client.py`
  - `tests/test_promptbranch_service_client.py`
  - `tests/test_promptbranch_container_api.py`
  - `tests/test_compose_timeout_policy.py`
  - `tests/test_cli_parser.py`
  - `tests/test_chatgpt_container_api.py`
  - `tests/test_promptbranch_cli.py`

Result: `408 passed`.

## Scope boundary

No submit order change. No answer extraction change. No sentinel/freshness gate change.
