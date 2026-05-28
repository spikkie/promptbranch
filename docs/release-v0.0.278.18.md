# Release v0.0.278.18

## Base

Built from `chatgpt_claudecode_workflow_v0.0.278.17.zip`.

## Reason

`v0.0.278.17` could still return a stale pre-submit assistant JSON payload while reporting response freshness as verified. The failing live check showed the fresh token in the service envelope, but the returned answer was the older `SUBMIT_CONFIRMATION_FAST_PATH_OK` payload.

## Changes

- Preserves warm-task hydration reuse from `v0.0.278.16`.
- Preserves submit-confirmation fast path from `v0.0.278.15`.
- Preserves latest-turn JSON fast return, but only after payload provenance is verified.
- Binds JSON extraction to assistant turns that appear after the pre-submit assistant-turn baseline.
- Excludes all pre-submit assistant turns from guarded JSON extraction.
- Removes `assistant_count_increased` as sufficient freshness evidence.
- Adds payload-provenance timing/evidence fields:
  - `response_payload_bound_to_post_submit_turn`
  - `response_payload_turn_index`
  - `response_payload_baseline_turn_index`
  - `response_payload_current_turn_count`
  - `response_pre_submit_payload_hashes_count`
  - `response_payload_seen_before_submit`

## Validation

- `python3 -m py_compile` over repository Python files.
- Focused pytest for browser client response extraction, warm hydration, stale-payload rejection, version, compose, and container API checks.

## Scope control

No line/slice state was advanced. This release only repairs the `.17` stale-answer correctness defect while preserving the intended `.16` warm hydration behavior.
