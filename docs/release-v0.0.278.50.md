# v0.0.278.50 — External-only retry refill timing diagnostics

Base artifact: `chatgpt_claudecode_workflow_v0.0.278.48.zip`

Purpose:

- Preserve the green `.48` submit behavior.
- Keep `/backend-api/f/conversation/prepare` excluded from submit confirmation.
- Add only external timing around the existing `.48` retry refill path.
- Do not refactor or instrument `_fill_chat_prompt` internals.

Behavioral boundary:

- Raw Enter remains the primary submit dispatch.
- Failed raw Enter still triggers the existing trusted-refill retry.
- Trusted-refill retry still calls the `.48` `_fill_chat_prompt` implementation unchanged.
- Retry Enter is still dispatched only by the existing `.48` retry path.
- Prepare-only traffic remains diagnostic evidence and cannot confirm submit.

New diagnostic field:

```text
submit_keyboard_enter_retry_result.retry_refill_external_timing
```

The timing object records phase timings around existing await boundaries:

```text
find_visible_chat_input
before_fill_diagnostics
fill_chat_prompt_call
after_fill_diagnostics
pre_dispatch_diagnostics
keyboard_event_probe_install
keyboard_dispatch
submit_confirmation_wait
keyboard_event_probe_collect
post_confirmation_diagnostics
post_submit_composer_state
```

The field is intentionally external-only so that the next run can determine where the `.48` delay occurs without collapsing the internal refill behavior as `.49` did.
