# v0.0.278.51 — monotonic-only fill-path timing diagnostics

Base: `chatgpt_claudecode_workflow_v0.0.278.48.zip`

This release is diagnostic-only. It keeps the `.48` submit and retry behavior intact while adding monotonic-only timing evidence inside the existing fill path.

## Scope

- Preserve raw Enter primary dispatch.
- Preserve `.48` prepare-only rejection and trusted-refill retry behavior.
- Preserve `/backend-api/f/conversation/prepare` exclusion from submit confirmation.
- Add `time.monotonic()` timing around existing fill-path awaits only.
- Do not add browser probes, waits, event listeners, dispatch changes, or fill-logic changes.

## New evidence

Retry fill evidence now exposes:

```text
submit_keyboard_enter_retry_result.fill_evidence.monotonic_timing
submit_keyboard_enter_retry_result.fill_evidence.attempts[*].monotonic_timing
submit_keyboard_enter_retry_result.fill_evidence.attempts[*].clear_evidence.monotonic_timing
```

The timing is intended to identify which existing `.48` fill await consumes the long readiness interval without collapsing the path like `.49` did.
