# Slice Horizon

## Current rolling horizon

| Version | Slice | Status | Release mode | Scope |
|---|---|---|---|---|
| v0.1.120 | Guarded multi-repository rollout execution and rollback evidence | repair_required | normal | original artifact remains non-adoptable; behavior delivered by repair successor |
| v0.1.120.1 | Checkpoint resume exit-code handling repair | accepted_historical | repair | caller-owned checkpoint return-code handling |
| v0.1.121 | Resumable release-set rollout recovery and operator reconciliation | repair_required | normal | original artifact misclassifies HTTP 429 as backend 403 |
| v0.1.121.1 | Backend 403/429 auth-bootstrap guardrail classification repair | accepted_current | repair | explicit-status challenge classification with accepted recovery behavior |
| v0.1.122 | Canonical MVP proof cycle 1 | active | normal | scope-frozen, machine-checkable ask/intake/validate/adopt/current/continue proof |
| v0.1.123 | Canonical MVP proof cycle 2 and final MVP verdict | planned_after_acceptance | normal | repeat from accepted v0.1.122 and close MVP only if both cycles are clean |

## Independence rule

Promptbranch and `promptbranch-method` develop independently. Method releases remain compatible with the accepted runtime contract `Promptbranch >= v0.1.116`; adoption of the generic release pipeline remains an explicit project decision.

## Repair horizon rule

Repair releases must not advance scope. `v0.1.121.1` is accepted/current and closes the `v0.1.121` repair line. `v0.1.122` and `v0.1.123` are normal proof releases; any repair between them resets the consecutive-cycle count.

## MVP finalization rule

Bounded parallel release-set wave execution is deferred post-MVP. The next two normal releases are reserved exclusively for canonical proof. Cycle 1 is not complete until `mvp_proof_cycle_passed` exists for `v0.1.122`; the final verdict remains unavailable until cycle 2 passes from accepted `v0.1.122`.

## Historical continuity

Historical continuity: v0.1.111, v0.1.111.2, v0.1.111.3, v0.1.111.4, v0.1.111.5, v0.1.111.5.2, v0.1.112, v0.1.113, v0.1.114, v0.1.114.2, v0.1.115, v0.1.115.1, v0.1.116, v0.1.117, v0.1.117.1, v0.1.118, v0.1.118.1, v0.1.119.
