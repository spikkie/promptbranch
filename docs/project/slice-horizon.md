# Slice Horizon

## Current rolling horizon

| Version | Slice | Status | Release mode | Scope |
|---|---|---|---|---|
| v0.1.119 | Read-only multi-repository release-set dependency planner | accepted_historical | normal | dependency ordering, waves, compatibility matrix and immutable target inspection |
| v0.1.120 | Guarded multi-repository rollout execution and rollback evidence | repair_required | normal | guarded execution and reverse rollback; original retry bytes remain non-adoptable |
| v0.1.120.1 | Checkpoint resume exit-code handling repair | accepted_current | repair | caller-owned checkpoint return-code handling and strict 10/10 adoption |
| v0.1.121 | Resumable release-set rollout recovery and operator reconciliation | repair_required | normal | recovery scope preserved; original bytes misclassify HTTP 429 as backend 403 |
| v0.1.121.1 | Backend 403/429 auth-bootstrap guardrail classification repair | active | repair | explicit-status challenge classification with unchanged recovery semantics |
| v0.1.122 | Bounded parallel release-set wave execution and concurrency evidence | planned_after_acceptance | normal | bounded isolated parallelism within dependency waves |

## Independence rule

Promptbranch and `promptbranch-method` develop independently. Method releases remain compatible with the accepted runtime contract `Promptbranch >= v0.1.116`; adoption of the generic release pipeline remains an explicit project decision.

## Repair horizon rule

Repair releases must not advance scope. `v0.1.121.1` preserves the complete normal scope of `v0.1.121` and repairs only the false promotion of HTTP 429 telemetry to backend 403 challenge evidence. The next normal scope remains `v0.1.122`.

## Current rolling horizon — v0.1.121.1 repair candidate

- `v0.1.119` — accepted historical release-set planner.
- `v0.1.120` — repair-required original guarded rollout artifact.
- `v0.1.120.1` — accepted/current checkpoint-resume repair baseline.
- `v0.1.121` — repair-required normal candidate with preserved recovery functionality.
- `v0.1.121.1` — active guardrail-classification repair candidate.
- `v0.1.122` — planned after acceptance: bounded parallel wave execution.

## Historical continuity

Historical continuity: v0.1.111, v0.1.111.2, v0.1.111.3, v0.1.111.4, v0.1.111.5, v0.1.111.5.2, v0.1.112, v0.1.113, v0.1.114, v0.1.114.2, v0.1.115, v0.1.115.1, v0.1.116, v0.1.117, v0.1.117.1, v0.1.118, v0.1.118.1.
