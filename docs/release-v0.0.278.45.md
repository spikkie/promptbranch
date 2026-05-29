# Release v0.0.278.45

## Summary

Conservative retry-fill repair after v0.0.278.43/v0.0.278.44 showed that slim trusted refill is safe for fast prompt verification but not safe as a direct submit-dispatch precondition.

## Baseline

Built behaviorally from `chatgpt_claudecode_workflow_v0.0.278.42.zip`.

## Changes

- Preserves the v0.0.278.42 submit order:
  - raw Enter primary;
  - trusted-refill + Enter retry second.
- Preserves v0.0.278.42 raw-Enter prepare-only fast-fail.
- Preserves fast latest-turn answer promotion from v0.0.278.40/v0.0.278.42.
- Adds a retry-only slim pre-fill probe:
  - performs fast trusted paste/marker verification;
  - records the slim pre-fill evidence;
  - does **not** dispatch Enter after the slim pre-fill.
- Runs the full v0.0.278.42 trusted refill/readiness path after the slim pre-fill and before retry Enter.

## New diagnostics

- `trusted_refill_retry_slim_prefill_used`
- `trusted_refill_retry_slim_prefill_seconds`
- `trusted_refill_retry_slim_prefill_evidence`
- `trusted_refill_retry_slim_prefill_verified`
- `trusted_refill_retry_dispatch_after_slim_prefill`
- `trusted_refill_retry_full_fill_after_slim_prefill_used`
- `trusted_refill_retry_full_fill_after_slim_prefill_seconds`

## Non-goals

- Does not make trusted-refill primary.
- Does not dispatch Enter after slim pre-fill.
- Does not change answer extraction.
- Does not weaken exact-marker submit causality checks.
