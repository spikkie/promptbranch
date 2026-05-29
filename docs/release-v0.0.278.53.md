# Release v0.0.278.53

## Purpose

Diagnostic-only retry post-fill settlement experiment built from `chatgpt_claudecode_workflow_v0.0.278.48.zip`.

## Baseline

- Base artifact: `chatgpt_claudecode_workflow_v0.0.278.48.zip`
- Rejected predecessors for baseline purposes: `.49`, `.51`, `.52`
- `.50` remains evidence-only and diagnostic-heavy, not the operator baseline.

## Scope

Add an explicit post-fill settle before retry Enter in the existing keyboard refill retry path.

## Behavior constraints

- Do not edit `_fill_chat_prompt` internals.
- Do not change trusted paste, clear, clipboard, paste dwell, or verification logic.
- Do not reclassify `/backend-api/f/conversation/prepare` as submit confirmation.
- Do not change primary raw Enter behavior.
- Do not change retry dispatch ordering except for the explicit post-fill settle before retry Enter.

## Diagnostic evidence

The retry result now includes:

```text
submit_keyboard_enter_retry_result.post_fill_settle
submit_keyboard_enter_retry_result.post_fill_settle_seconds
submit_keyboard_enter_retry_result.post_fill_settle_observed_seconds
```

Default settle duration:

```text
8.0 seconds
```

Operator override for experiments:

```bash
PROMPTBRANCH_KEYBOARD_ENTER_RETRY_POST_FILL_SETTLE_SECONDS=8
```

## Expected interpretation

If this release turns green and submits via `/backend-api/f/conversation`, the missing readiness transition is likely a post-fill/pre-dispatch settle interval.

If this release remains prepare-only, timing alone is insufficient and the next diagnostic should look for a specific UI/backend readiness state rather than editing fill internals.
