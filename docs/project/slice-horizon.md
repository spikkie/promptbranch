# Rolling Slice Horizon

## Purpose

The rolling slice horizon keeps the main Promptbranch goal visible without pretending the full design is knowable upfront. It provides 4–5 upcoming slices, exactly one active slice, and clear replanning rules.

## Active horizon

| Version | Slice | Status | Scope | Out of scope |
|---|---|---|---|---|
| v0.1.101 | Read-only command result diagnosis and blocked/failed classification | active | Classify read-only command outcomes without correction or file mutation | correction, file writes, deployment |
| v0.1.102 | Correction-plan generation without file mutation | planned_after_acceptance | Produce a bounded correction plan from diagnosis evidence without writing files | file mutation, deployment, adoption |
| v0.1.103 | First controlled file mutation in sandboxed fixture only | planned | Perform the first mutation only inside an explicit sandbox fixture with before/after evidence | production files, deployment, Kubernetes |
| v0.1.104 | Sandbox mutation verification and rollback evidence gate | planned | Verify sandbox mutation result evidence and define rollback/stop gates before broader correction workflows | production mutation, deployment |
| v0.1.105 | Sandbox correction promotion readiness check | planned | Decide whether sandbox-only correction evidence is ready for broader controlled correction workflows without deployment | production mutation, deployment |

## Deferred slice

First controlled read-only validation command execution was originally the next post-v0.1.98 slice. It is explicitly deferred to `v0.1.100` so `v0.1.99` can make slice derivation and architecture decisions repo-authoritative before command execution begins.

## Slice authority block

Every normal release request should be able to produce this block from repo files:

```text
baseline: <accepted/current artifact>
release_mode: normal
active_mvp: MVP-1 loop-based problem-solving engine
architecture_goal: controlled problem-solving loop
active_slice: <current candidate slice>
next_slice_after_acceptance: <next planned normal slice>
scope_advance_allowed: true
repair_scope_advance_allowed: false
architecture_invariants_checked: true
control_surface_validated: true
```

If this block cannot be produced from `docs/project/plan-state.json` and the required Markdown docs, no release should be packaged.

## Repair horizon rule

Repair releases must preserve the current active normal slice and set `scope_advance_allowed=false`. They must not change the rolling horizon unless an explicit decision says the change becomes effective in the next normal release.

## Replanning rule

A normal release may update the rolling horizon when:

1. an architecture decision is recorded in `docs/project/decisions.md`;
2. `docs/project/plan-state.json` is updated;
3. this file is updated;
4. `pb project validate-control-surface --json` passes;
5. the release remains narrow and testable.
