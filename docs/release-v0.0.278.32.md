# Release v0.0.278.32

## Scope

Repair release for the old-task stale-guard browser ask path.

This release keeps the v0.0.278.30 keyboard-Enter primary submit path and the v0.0.278.31 backend-first answer probing model. It narrows the next defect: when submit is confirmed but no fresh parseable assistant answer is found, the service must return structured timeout evidence before the CLI HTTP client times out.

## Changes

- Bounded `submit_confirmed_answer_timeout` under the service-client budget.
- Added service-client budget diagnostics for backend-first answer waits:
  - `backend_first_answer_service_client_budget_ms`
  - `backend_first_answer_timeout_reserve_ms`
  - `backend_first_answer_budget_elapsed_before_wait_ms`
  - `backend_answer_wait_timeout_ms`
- Added backend assistant-turn qualification fields:
  - `backend_answer_qualification_status`
  - `backend_answer_assistant_turn_create_time`
  - `backend_answer_assistant_turn_update_time`
  - `backend_answer_assistant_turn_status`
  - `backend_answer_assistant_turn_end_turn`
  - `backend_answer_assistant_turn_content_type`
  - `backend_answer_text_length`
  - `backend_answer_text_sha256_12`
  - `backend_answer_text_preview`
  - `backend_answer_freshness_verified`
  - `backend_answer_freshness_reason`
- Preserved strict fresh-marker validation: marker-missing backend candidates remain rejected.
- Added top-level timeout diagnostics in the service response model via `backend_answer_diagnostics`.

## Validation

- `python3 -m compileall -q .`
- `pytest -q tests/test_project_list_browser_client.py`
- focused CLI/container/parser/API tests
- clean extracted ZIP validation

## Adoption note

Do not adopt this release unless the stale-guard run returns either:

- a fresh answer with `response_freshness_verified=true`, or
- a structured `submit_confirmed_answer_timeout` result before the CLI read timeout, with backend qualification fields populated.
