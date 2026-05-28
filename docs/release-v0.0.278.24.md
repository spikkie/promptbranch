# Release v0.0.278.24

Base release: v0.0.278.23
Release type: normal diagnostic repair release

## Reason

`v0.0.278.23` proved that trusted prompt paste works and that the stale-answer guard remains fail-closed, but live old-task asks still failed because only `/backend-api/f/conversation/prepare` requests were observed after submit. No marker-bearing message-submit request or backend commit was proven.

`v0.0.278.24` models the prepare phase explicitly so the failure is no longer collapsed into the generic `network_submit_request_not_observed` bucket.

## Scope

- Preserve trusted prompt input from v0.0.278.23.
- Preserve request-marker response freshness guard from v0.0.278.19.
- Preserve safe fail-closed submit causality behavior from v0.0.278.20 through v0.0.278.23.
- Add first-class prepare-only evidence fields.
- Return the specific `submit_prepare_without_message_commit` reason when prepare is observed but no final marker-bearing message submission follows.

## Files changed

- `promptbranch_browser_auth/client.py`
- `tests/test_project_list_browser_client.py`
- version metadata files
- release documentation

## Validation performed

- `python3 -m py_compile` for repository Python files.
- Focused pytest for browser client behavior and version/container/compose checks.
- ZIP hygiene verification before packaging.

## No slice or line advanced

This release does not advance any unrelated feature slice or architectural line. It is limited to submit causality diagnostics and fail-closed behavior for browser-backed `pb ask`.
