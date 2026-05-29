# v0.0.278.52 — call-site-only retry fill timing

## Intent

Build from `chatgpt_claudecode_workflow_v0.0.278.48.zip` and add only call-site timing around the existing retry `_fill_chat_prompt(...)` call.

## Scope

- Preserve `.48` submit behavior.
- Preserve `/backend-api/f/conversation/prepare` exclusion from submit confirmation.
- Do not edit `_fill_chat_prompt` internals.
- Do not edit trusted paste, clear, clipboard, paste dwell, or verification logic.
- Do not add probes, waits, event listeners, or browser-side instrumentation.

## New evidence

`submit_keyboard_enter_retry_result.fill_call_site_timing`

The timing records the monotonic start/end/duration around the single existing call-site await:

```text
await self._fill_chat_prompt(page, input_locator, prompt=prompt)
```

## Notes

This release is diagnostic-only. It is meant to distinguish `.48` fill-call duration from the failed `.49`/`.51` fast-fill behavior without changing the fill implementation.
