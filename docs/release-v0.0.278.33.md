# Release v0.0.278.33

## Scope

Builds on `chatgpt_claudecode_workflow_v0.0.278.32.zip`.

This release hardens the browser-backed `pb ask` submit confirmation path after the `.32` diagnostic showed a prepare-only/no-commit run with a transient backend conversation-detail `503` during commit verification.

## Changes

- Classify transient backend conversation-detail HTTP responses during backend task-message commit probing.
- Retry backend conversation-detail reads inside the bounded post-prepare commit window.
- Preserve backend-detail diagnostics in submit evidence:
  - `backend_detail_http_status`
  - `backend_detail_http_statuses`
  - `backend_detail_transient_error_count`
  - `backend_detail_retry_count`
  - `backend_detail_temporarily_unavailable`
- Distinguish `submit_backend_detail_temporarily_unavailable_timeout` from ordinary `backend_commit_after_prepare_not_found`.
- Retry keyboard Enter once with a trusted refill when the primary Enter path fails as prepare-only/no-commit or backend-detail temporary unavailable.
- Keep backend commit confirmation mandatory before answer waiting.

## Safety properties

- No URL-only or UI-idle signal is treated as success.
- Prepare-only remains fail-closed unless a backend user-turn commit is subsequently verified.
- The keyboard retry does not bypass the stale-answer gate; it only gets another chance to produce a backend user-message commit.
- Answer waiting still starts only after submit confirmation.

## Validation

- `python3 -m py_compile promptbranch_browser_auth/client.py tests/test_project_list_browser_client.py`
- `pytest -q tests/test_project_list_browser_client.py`

