# Release v0.1.99 — Rolling slice horizon and architecture-decision protocol

## Baseline

- Accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.98.zip`
- Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.99.zip`
- Release mode: normal
- Active MVP: MVP-1 loop-based problem-solving engine

## Purpose

This slice makes next-slice definition part of the repository control surface before Promptbranch starts real command execution.

`v0.1.98` made plan-state validation executable. `v0.1.99` extends that into a rolling 4–5 slice horizon and a documented architecture-decision protocol.

## In scope

- Add `docs/project/architecture.md` with fixed architecture invariants and adaptive design boundaries.
- Add `docs/project/slice-horizon.md` with the rolling five-slice horizon.
- Extend `docs/project/plan-state.json` with:
  - `architecture_goal`
  - `architecture_invariants`
  - `slice_derivation_inputs`
  - `rolling_slice_horizon`
  - `replan_rules`
- Add `pb project next-slice --json`.
- Extend `pb project validate-control-surface --json` so architecture and slice-horizon docs are required.
- Record the explicit planning decision that first controlled read-only validation command execution is deferred to `v0.1.100`.

## Out of scope

- read-only validation command execution
- file mutation
- deployment
- Kubernetes mutation
- Project Source behavior change
- artifact adoption behavior change
- ChatGPT Project deletion

## Rolling horizon after this candidate

```text
v0.1.99 — Rolling slice horizon and architecture-decision protocol
v0.1.100 — First controlled read-only validation command execution
v0.1.101 — Read-only command result diagnosis and blocked/failed classification
v0.1.102 — Correction-plan generation without file mutation
v0.1.103 — First controlled file mutation in sandboxed fixture only
```

## Validation expectation

Focused validation should include:

- `tests/test_project_control_surface.py`
- `tests/test_promptbranch_version.py`
- CLI smoke for `pb project validate-control-surface --json`
- CLI smoke for `pb project next-slice --json`
- compileall
- shell syntax
- Artifact Guardian
- artifact verify

Full acceptance still requires release-control `--run-all-tests --strict-source-kind-matrix --adopt-after-validation` and `pb artifact current --json` alignment.
