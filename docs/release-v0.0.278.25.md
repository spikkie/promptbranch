# Release v0.0.278.25

## Base

Built from `chatgpt_claudecode_workflow_v0.0.278.24.zip`.

## Reason

Capture the `/backend-api/f/conversation/prepare` response and observe a bounded post-prepare transport/backend-commit window before deciding final message send is impossible.

## Changes

- Treat prepare-only as a phase with response and post-prepare diagnostics.
- Capture all post-click request/response summaries alongside backend write summaries.
- After prepare-only evidence, poll backend conversation detail for the current request marker in a bounded commit window.
- Confirm submit causality as `backend_commit_after_prepare` when the backend commit appears.
- Fail closed as `submit_prepare_without_backend_commit` when prepare appears but no backend commit is found.
- Preserve trusted paste input, request-marker response freshness, and stale-answer fail-closed behavior.

## Validation

- `python3 -m compileall -q ...`
- Focused browser-client tests
- Focused version/container/compose/CLI tests
- ZIP hygiene verification

## Scope control

No accepted baseline advancement is implied by this release candidate. Adoption requires live old-task validation returning the fresh token.
