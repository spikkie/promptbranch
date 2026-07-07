# v0.1.103.10.71 — final verdict aggregation maps live_bootstrap_guardrail cascade to LIVE_BLOCKED

## Scope

This repair keeps the `v0.1.103.10.69` `install.sh` strict all-all gate and the `v0.1.103.10.70` status vocabulary. It fixes the actual release-control final verdict aggregation path used after `--run-all-tests --run-external-live-tests --require-chatgpt-live-validation`.

## Defect

`v0.1.103.10.70` could still emit `all_tests_final_verdict: FIX` when `release-live-continuous` appended `status: live_bootstrap_guardrail` after a valid project/conversation payload in the mixed `live_project_ensure` log. The summary JSON reader selected the valid project payload, set the step status to generic `failed`, and therefore counted the failure as product repair evidence.

## Repair

The all-tests summary aggregation now normalizes `live_project_ensure` to `live_bootstrap_guardrail` when the raw mixed log contains terminal bootstrap guardrail evidence. Downstream `skipped_blocked_by_live_bootstrap_guardrail` steps remain failed/skipped live steps, but the final verdict becomes `LIVE_BLOCKED`, not product `FIX`, when artifact/product validation is otherwise clean.

## Preserved behavior

- Adoption remains refused with `--adopt-after-validation` whenever external live validation fails.
- Failed live steps are preserved in `failed_steps`.
- `artifact_guard` remains independently evaluated and can still pass.
- No Cloudflare/rate-limit bypass was added.
- No host-CDP/session-manager path was added.
- No copied-profile trust was added.

## Validation

Focused validation covers the replay/static failure shape from `v0.1.103.10.70`: `live_project_ensure` contains raw `live_bootstrap_guardrail`, downstream live steps are skipped with `skipped_blocked_by_live_bootstrap_guardrail`, `artifact_guard` passes, and final verdict is `LIVE_BLOCKED`.
