# Release v0.1.98 — Plan authority and anti-drift control-surface gate

## Type

Normal candidate.

## Baseline

`chatgpt_claudecode_workflow-2_v0.1.97.1.zip` accepted/current.

## Scope

- Add `docs/project/plan-state.json` as the machine-readable continuation authority.
- Add `pb project validate-control-surface --json`.
- Fail closed when the current baseline, active candidate, active MVP, normal/repair lineage, DoD, release-status, decisions, migration, or next-slice metadata drift.
- Update stale current-state sections in `docs/project/status.md` and `docs/project/plan.md`.
- Defer first controlled read-only validation command execution to `v0.1.99`.

## Out of scope

- Read-only validation command execution.
- File mutation from the loop engine.
- Deployment or Kubernetes mutation.
- Project Source behavior changes.
- Artifact adoption behavior changes.
- ChatGPT Project deletion.

## Validation target

`pb project validate-control-surface --json` must pass before packaging and before release-control adoption.
