# Release v0.0.278.35

## Scope

Builds on `chatgpt_claudecode_workflow_v0.0.278.34.zip`.

This release does not add a new submit strategy.  It keeps keyboard-submit
commit confirmation intact and changes only post-submit answer retrieval and
failure reporting.

## Changes

- Compare backend, DOM post-submit, and visible UI answer extraction after a
  confirmed user-turn commit.
- If backend conversation-detail returns a parseable but request-marker-missing
  assistant candidate, record it and continue to DOM/visible UI extraction
  instead of repeatedly returning the same backend candidate.
- Add response extraction candidate diagnostics with source, selector, text
  length, hash, preview, marker presence, parse status, acceptance state, and
  rejection reason.
- Keep strict freshness protection: only candidates containing the request
  marker/sentinel can be accepted when request binding is required.
- Enforce the absolute ask deadline inside response polling, extraction,
  completion probing, and debug artifact capture.
- Skip final response probes and debug screenshots when the deadline reserve is
  exhausted so the service can return `submit_confirmed_answer_timeout` before
  the client read timeout.

## Validation

- `python3 -m py_compile promptbranch_browser_auth/client.py`
- focused pytest validation for browser client response extraction and timeout
  behavior
- ZIP hygiene validation after packaging

## Adoption guidance

Do not adopt this release unless the stale-guard run either succeeds with the
fresh sentinel or returns a structured `submit_confirmed_answer_timeout` before
`service_client_read_timeout`.  If it fails, inspect `response_extraction_candidates`
to compare backend, DOM, and visible answer candidates.
