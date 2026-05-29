# v0.0.278.57 — .48 Enter dispatch with one-shot answer wait

## Intent

Restore the simple `pb ask "prompt"` behavior:

1. fill the composer once;
2. press Enter once using the existing v0.0.278.48 keyboard-primary dispatch path;
3. do not perform refill/retry/send-button recovery by default;
4. proceed to the normal answer wait after Enter instead of short-circuiting when submit-confirmation diagnostics are disabled or inconclusive.

## Why

v0.0.278.56 correctly removed expensive retry/refill behavior, but it also skipped the response wait because the fast path did not set submit-confirmation evidence. That made the command return `submit_causality_not_confirmed` before waiting for an answer.

## Behavior

- Keyboard Enter remains the default submit dispatch.
- `CHATGPT_KEYBOARD_ENTER_COMMIT_RETRY` now defaults to disabled.
- Retry/refill can only run if explicitly re-enabled through the environment for diagnostics.
- A primary one-shot Enter dispatch is allowed to continue into the normal answer wait.
- Response extraction still owns freshness and stale-answer protection.

## Validation

- Python compilation.
- Focused browser-client submit tests.
- CLI option preservation checks.
- ZIP hygiene verification from clean extraction.
