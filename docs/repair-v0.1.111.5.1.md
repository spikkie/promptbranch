# v0.1.111.5.1 — Empty-step-safe ETA progress and stable range countdown

## Baseline

- Accepted/current: `v0.1.111.5`
- Candidate: `v0.1.111.5.1`
- Release mode: repair
- Scope advance: forbidden

## Problem

The accepted strict release run emitted ten `bad array subscript` diagnostics because post-step progress called `run_all_emit_progress` without a current step and the shell indexed `all_test_step_started_epoch` with an empty key. The same run also showed an ETA high range widening from `00:12..00:15` to `00:04..08:49` while the active plan shrank because only the midpoint triggered the stable-countdown clamp.

## Corrective contract

1. Initialise current-step start time to zero and index the associative array only for a non-empty step name.
2. Pass the previous ETA high bound into the named-step estimator.
3. While the active plan is unchanged or shrinking, clamp both midpoint and high bound to their previous values.
4. Preserve `low <= midpoint <= high` after clamping.
5. Permit expansion when the active plan genuinely expands or an unknown estimate becomes known.
6. Preserve backward compatibility when an older progress snapshot contains a midpoint but no high bound.
7. Keep all ETA errors informational and unable to affect validation authority.

## Required evidence

- executable shell regression for progress with no active step;
- midpoint-decreasing/high-expanding regression;
- active-plan expansion regression;
- focused ETA and release-control tests;
- packaged-byte validation;
- strict host 10/10 validation with zero `bad array subscript` diagnostics;
- evidence-bound adoption and accepted/current verification.

## Authority boundary

`v0.1.112 — PBAI-001 declaration and structural validation` remains blocked until this corrective is accepted.
