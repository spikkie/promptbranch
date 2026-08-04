# Slice Horizon

## Current rolling horizon

| Version | Slice | Status | Release mode | Scope |
|---|---|---|---|---|
| v0.1.121 | Resumable release-set rollout recovery and operator reconciliation | repair_required | normal | original artifact misclassifies HTTP 429 as backend 403 |
| v0.1.121.1 | Backend 403/429 auth-bootstrap guardrail classification repair | accepted_historical | repair | explicit-status challenge classification with accepted recovery behavior |
| v0.1.122 | Canonical MVP proof cycle 1 instrumentation | accepted_current | normal | strict release passed; formal proof was not counted because finalizer repair is required |
| v0.1.122.1 | MVP proof finalizer fail-closed evidence repair | active | repair | project-level current parsing, exact SHA binding, preflight ordering, and truthful exit status |
| v0.1.123 | Canonical MVP proof cycle 1 | planned_after_acceptance | normal | first clean ask/intake/validate/adopt/current/continue proof from accepted repair baseline |
| v0.1.124 | Canonical MVP proof cycle 2 and final MVP verdict | planned | normal | second consecutive clean proof and earliest formal MVP completion |

## Independence rule

Promptbranch and `promptbranch-method` develop independently. Method releases remain compatible with the accepted runtime contract `Promptbranch >= v0.1.116`; adoption of the generic release pipeline remains an explicit project decision.

## Repair horizon rule

Repair releases must not advance scope. `v0.1.122.1` repairs proof-control correctness only and cannot count as a normal proof cycle. Because `v0.1.122` required a repair after adoption, the consecutive normal proof count remains zero.

## MVP finalization rule

Bounded parallel release-set wave execution remains deferred post-MVP. `v0.1.123` is the first clean normal proof cycle and `v0.1.124` is the second. The final MVP verdict is unavailable unless both produce `mvp_proof_cycle_passed` consecutively without an intervening repair.

## Historical continuity

Historical continuity: v0.1.111, v0.1.111.2, v0.1.111.3, v0.1.111.4, v0.1.111.5, v0.1.111.5.2, v0.1.112, v0.1.113, v0.1.114, v0.1.114.2, v0.1.115, v0.1.115.1, v0.1.116, v0.1.117, v0.1.117.1, v0.1.118, v0.1.118.1, v0.1.119, v0.1.120, v0.1.120.1.
