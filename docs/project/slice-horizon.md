# Slice Horizon

## Current rolling horizon

| Version | Slice | Status | Release mode | Scope |
|---|---|---|---|---|
| v0.1.118 | Resumable/importable release-pipeline evidence and recovery | accepted_historical | normal | incremental checkpoints, read-only import and guarded resume without mutation replay |
| v0.1.118.1 | Deterministic canonical rebuild and failed-attempt identity binding | accepted_historical | repair | deterministic ZIP bytes, provisional identity and automatic exact-source recovery |
| v0.1.119 | Read-only multi-repository release-set dependency planner | accepted_current | normal | dependency ordering, waves, compatibility matrix and immutable target inspection |
| v0.1.120 | Guarded multi-repository rollout execution and rollback evidence | active | normal | exact plan binding, explicit per-repository pipeline execution, reverse rollback and tamper-evident evidence |
| v0.1.121 | Resumable release-set rollout recovery and operator reconciliation | planned_after_acceptance | normal | interrupted-run import/resume and controlled recovery from incomplete rollback |

## Independence rule

Promptbranch and `promptbranch-method` develop independently. Method releases remain compatible with the accepted runtime contract `Promptbranch >= v0.1.116`; adoption of the generic release pipeline remains an explicit project decision.

## Repair horizon rule

Repair releases must not advance normal scope. `v0.1.119` is accepted/current. `v0.1.120` is the active normal slice and grants mutation authority only through an exact compatible plan, explicit complete lifecycle confirmation, repository-owned release contracts, and mandatory reverse rollback evidence.

## Current rolling horizon — v0.1.120 normal candidate

- `v0.1.118` — accepted historical normal release.
- `v0.1.118.1` — accepted historical repair release.
- `v0.1.119` — accepted/current read-only release-set planner.
- `v0.1.120` — active normal candidate: guarded release-set rollout and rollback evidence.
- `v0.1.121` — planned after acceptance: resumable rollout recovery and operator reconciliation.

## Historical continuity

Historical continuity: v0.1.111, v0.1.111.2, v0.1.111.3, v0.1.111.4, v0.1.111.5, v0.1.111.5.2, v0.1.112, v0.1.113, v0.1.114, v0.1.114.2, v0.1.115, v0.1.115.1, v0.1.116, v0.1.117, v0.1.117.1.
