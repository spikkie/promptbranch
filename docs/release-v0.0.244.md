# Release v0.0.244

## Scope

Read-only Artifact Intake MVP cockpit remediation planning.

## Changes

- Added `remediation_plan` to `pb artifact mvp-status --json`.
- Added top-level `next_safe_actions` derived from the remediation plan.
- Safe actions emitted by `mvp-status` are inspection-only and marked with `mutates_state: false`.
- Runtime/source baseline mismatch now includes explicit read-only inspection commands and an operator-decision step.
- No candidate/no-artifact states now include an explicit operator-decision step to create a real release-candidate protocol turn.

## Safety

`pb artifact mvp-status` remains read-only. It does not download, verify-write, migrate, test, adopt, mutate Project Sources, update registries, or advance artifact/source state.

## Validation

Focused CLI/parser tests and ZIP hygiene checks were run for this release artifact.
