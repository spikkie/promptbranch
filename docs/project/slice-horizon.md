# Slice Horizon

## Current rolling horizon

| Version | Slice | Status | Release mode | Scope |
|---|---|---|---|---|
| v0.1.117 | PBAI compliance inventory and evidence-bound generic release pipeline | accepted_historical | normal | inventory, local proof, explicit Git, source publication, evidence-bound adoption, current verification |
| v0.1.117.1 | Immutable release identity and hash-bound evidence reuse | accepted_current | repair | same-version hash immutability, idempotent rerun, canonical evidence binding |
| v0.1.118 | Resumable/importable release-pipeline evidence and recovery | active | normal | incremental checkpoints, read-only import, guarded resume without mutation replay |
| v0.1.119 | Read-only multi-repository release-set dependency planner | planned_after_acceptance | normal | dependency ordering and compatibility matrix |
| v0.1.120 | Guarded multi-repository rollout execution and rollback evidence | planned | normal | explicit per-repository execution, rollback and final project consistency |

## Independence rule

Promptbranch and `promptbranch-method` develop independently. Method releases remain compatible with the accepted runtime contract `Promptbranch >= v0.1.116`; adoption of the generic release pipeline remains an explicit project decision.

## Repair horizon rule

Repair releases must not advance normal scope. `v0.1.117.1` is accepted/current; `v0.1.118` is therefore permitted to advance the next normal slice.

## Historical continuity

The established release history remains authoritative in the release and candidate records. Historical entries do not consume machine-horizon slots.

## Current rolling horizon — v0.1.118 normal candidate

- `v0.1.117.1` — accepted/current repair baseline.
- `v0.1.118` — active normal candidate: resumable/importable release-pipeline evidence and recovery.
- `v0.1.119` — planned after acceptance: read-only multi-repository release-set dependency planner.
- `v0.1.120` — planned: guarded multi-repository rollout execution and rollback evidence.


## Historical continuity

Historical continuity: v0.1.111, v0.1.111.2, v0.1.111.3, v0.1.111.4, v0.1.111.5, v0.1.111.5.2, v0.1.112, v0.1.113, v0.1.114, v0.1.114.2, v0.1.115, v0.1.115.1, v0.1.116.
