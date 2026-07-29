# v0.1.111.5.2 — Null-safe previous active-step ETA state

## Baseline

- Accepted/current: `v0.1.111.5`
- Rejected candidate: `v0.1.111.5.1`
- Candidate: `v0.1.111.5.2`
- Release mode: repair
- Scope advance: forbidden

## Problem

The `v0.1.111.5.1` strict host run proved the empty-current-step shell repair and stable ETA range countdown, but top-level progress still passed `None` when the previous progress snapshot had no `active_steps` value. `estimate_named_step_eta` attempted to iterate that value and emitted `TypeError: 'NoneType' object is not iterable`. ETA remained informational, but the candidate violated the zero-`eta_calculation_failed` acceptance criterion and was not adopted.

## Corrective contract

1. Normalise missing or null `previous_active_steps` to an empty sequence at the release-controller caller boundary.
2. Independently normalise `previous_active_steps` inside the estimator so direct callers and older state cannot trigger the exception.
3. Preserve empty-current-step associative-array safety from `v0.1.111.5.1`.
4. Preserve midpoint and high-bound countdown clamping while the active plan is unchanged or shrinking.
5. Permit ETA expansion only when the active plan expands or prior state is absent.
6. Keep all ETA failures informational and unable to affect validation, fail-fast, transport independence, adoption, or accepted/current authority.

## Required evidence

- unit regressions for omitted and explicit-null previous active-step state;
- release-controller contract regression for null/missing `active_steps`;
- empty-current-step and stable-range regressions remain green;
- packaged-byte validation;
- strict host 10/10 validation with zero `TypeError`, zero `eta_calculation_failed`, and zero `bad array subscript`;
- evidence-bound adoption and accepted/current verification.

## Authority boundary

`v0.1.112 — PBAI-001 declaration and structural validation` remains blocked until this corrective is accepted.
