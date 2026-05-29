# Release v0.0.278.54 — Retry refill send-button click dispatch

## Base artifact

```text
chatgpt_claudecode_workflow_v0.0.278.48.zip
```

## Target artifact

```text
chatgpt_claudecode_workflow_v0.0.278.54.zip
```

## Scope

This is a narrow diagnostic release. It tests whether the retry path fails because it dispatches the verified refilled prompt with keyboard Enter.

## Changes

- Keeps primary raw Enter submit dispatch unchanged.
- Keeps `_fill_chat_prompt` unchanged from v0.0.278.48.
- Keeps `/backend-api/f/conversation/prepare` excluded from submit confirmation.
- After primary raw Enter fails without a marker-bound backend commit, the retry path still performs trusted refill.
- After refill verification, the retry path clicks a visible enabled send-ready button instead of pressing Enter.
- Adds retry evidence for `send_button_click` dispatch.

## New retry evidence

```text
submit_keyboard_enter_retry_result.variant = keyboard_enter_refill_send_button_click_retry
submit_keyboard_enter_retry_result.dispatch_key = send_button_click
submit_keyboard_enter_retry_result.dispatch_method = send_button_click
submit_keyboard_enter_retry_result.send_button_click_dispatch
submit_keyboard_enter_retry_result.send_button_click_used
```

## Safety

This release does not weaken stale-answer protection and does not accept prepare-only traffic as submit confirmation. Exact marker/sentinel submit causality remains required.

## Expected interpretation

```text
If v0.0.278.54 succeeds, retry Enter was likely the broken dispatch path.
If it still produces prepare-only, the problem is deeper than keyboard-vs-click retry dispatch.
```
