# Slice Horizon

## Current rolling horizon

| Version | Slice | Status | Release mode | Scope |
|---|---|---|---|---|
| v0.1.117.1 | Immutable release identity and hash-bound evidence reuse | active repair | repair | same-version hash immutability, idempotent rerun, canonical evidence binding |
| v0.1.115.1 | Release-live profile ownership handoff repair | accepted_historical | repair | operational PBAI baseline |
| v0.1.116 | PBAI templates, migration, differential validation, and first domain-module proof | accepted_current | normal | stable runtime contract and domain-module proof |
| v0.1.117 | PBAI compliance inventory and evidence-bound generic release pipeline | active | normal | inventory, local proof, explicit Git, source publication, evidence-bound adoption, current verification |
| v0.1.118 | Resumable/importable release-pipeline evidence and recovery | planned_after_acceptance | normal | resume after partial failure without replaying successful mutation phases |
| v0.1.119 | Multi-repository release-set dependency planner | planned | normal | read-only dependency ordering and compatibility matrix |
| v0.1.120 | Guarded multi-repository rollout execution and rollback evidence | planned | normal | explicit per-repository execution, rollback and final project consistency |

## Independence rule

Promptbranch and `promptbranch-method` develop independently. Method releases remain compatible with the accepted runtime contract `Promptbranch >= v0.1.116`; a later Method release may adopt the `v0.1.117` pipeline through an explicit compatibility change.

## Repair horizon rule

Repair releases must not advance normal scope. A normal slice advances only after accepted/current evidence and the project control surface agree.

## Historical continuity

The current six-slice machine horizon follows the established sequence: `v0.1.111`, `v0.1.111.2`, `v0.1.111.3`, `v0.1.111.4`, `v0.1.111.5`, `v0.1.111.5.2`, `v0.1.112`, `v0.1.113`, `v0.1.114`, `v0.1.114.2`, `v0.1.115`, and `v0.1.115.1`. Historical entries remain release evidence but do not consume machine-horizon slots.

## Current rolling horizon — v0.1.117.1 repair

- `v0.1.117` — accepted/current normal baseline.
- `v0.1.117.1` — active repair: Immutable release identity and hash-bound evidence reuse.
- `v0.1.118` — planned after acceptance: Resumable/importable release-pipeline evidence and recovery.
- `v0.1.119` — planned: multi-repository release-set dependency planner.
- `v0.1.120` — planned: guarded multi-repository rollout execution and rollback evidence.

Repair horizon rule: a repair must not advance normal scope.
