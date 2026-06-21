# Repair v0.1.84.2 — acknowledge ChatGPT 429 modal and wait before continuing

## Base release

`v0.1.84.1` focused repair candidate.

## Repair version

`v0.1.84.2`

## Reason

Live browser validation can hit ChatGPT's conversation-history guardrail modal:

```text
Too many requests
You're making requests too quickly. We've temporarily limited access to your conversations to protect your data.
```

The previous automation could detect the modal and click `Got it`, but short call-site modal timeouts could still fail the operation before the human-equivalent recovery flow completed. Operators manually click `Got it` and wait briefly before continuing; the browser layer should do the same instead of turning a recoverable 429 modal into a timeout failure.

## Scope

Repair-only. No orchestration ledger scope advanced. No accepted-event write path was added.

## Changes

- Added configurable `rate_limit_modal_ack_wait_seconds` with default `60.0` seconds.
- When a conversation-history rate-limit modal is visible in a history-sensitive operation, browser automation clicks `Got it`, records acknowledgement telemetry, waits the acknowledgement cooldown, and then continues polling instead of failing on the original short timeout.
- The acknowledgement wait satisfies the persisted modal cooldown for the current operation, avoiding a duplicate post-clear wait.
- Non-history operations that explicitly skip conversation-history cooldown still click the modal but do not wait on the acknowledgement cooldown.
- Added regression coverage for the click-then-wait behavior and cooldown satisfaction telemetry.

## Validation performed

- Focused rate-limit modal acknowledgement regression tests.
- Existing non-history cooldown-skip regression.
- Version test.
- compileall and shell syntax checks.
- Artifact Guardian ZIP validation.

## No slice advancement

This repair does not advance beyond `v0.1.84` ledger validation. It fixes live/browser test rate-limit handling only. Accepted/current remains `v0.1.79` until promotion/adoption evidence exists.
