# Release v0.1.128.2.6.1.1.2.1.1

## Purpose

Runtime-authority isolation corrective following the distributed `v0.1.128.2.6.1.1.2.1` candidate.

## Repair

- Static `project authority validate` no longer resolves host/runtime authorities when `include_runtime=False`; runtime domains are reported as `deferred_runtime`.
- Runtime validation still resolves the configured runtime authority when `include_runtime=True`.
- Runtime-authority absence tests isolate `PROMPTBRANCH_PROJECT_STATE_HOME` so they cannot read the operator's live Project registry.
- `VERSION` remains the sole mutable release-version authority for executable and packaging code.

## Baseline

Accepted/current remains `v0.1.128.2.6.1.1.1` until this exact candidate completes the canonical lifecycle.

## Construction validation

- Authority/control/release focused gate: 62/62 green.
- Application structural coverage: 62/62 nodeids green by bounded constituent execution.
- Current version literal scan across executable/packaging sources: zero violations; `VERSION` remains sole mutable version authority.
- Final exact ZIP determinism, Artifact Guardian, and clean-extraction regression remain required before handoff.
