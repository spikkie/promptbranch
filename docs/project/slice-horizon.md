# Slice Horizon

## Current rolling horizon

| Version | Slice | Status | Release mode | Scope |
|---|---|---|---|---|
| v0.1.122.1 | MVP proof finalizer fail-closed evidence repair | accepted_historical | repair | project-level current parsing, exact SHA binding, preflight ordering, and truthful exit status |
| v0.1.123 | Canonical MVP proof cycle 1 attempt | accepted_current_proof_not_counted | normal | release/adoption passed, but exact chronological candidate intake was absent |
| v0.1.123.1 | Complete proof lifecycle ownership in `pb ask` | active | repair | exact request/message/answer correlation and one-command fail-closed lifecycle |
| v0.1.124 | Canonical MVP proof cycle 1 | planned_after_acceptance | normal | first complete one-command ask/intake/validate/adopt/current/continue proof |
| v0.1.125 | Canonical MVP proof cycle 2 and final verdict | planned_after_acceptance | normal | second consecutive complete one-command proof and earliest formal MVP completion |

## Independence rule

Promptbranch and `promptbranch-method` develop independently. Method releases remain compatible with the accepted runtime contract `Promptbranch >= v0.1.116`; adoption of the generic release pipeline remains an explicit project decision.

## Repair horizon rule

Repair releases must not advance scope. `v0.1.123.1` can make the proof workflow operable, but it cannot count as one of the required normal proof cycles. `v0.1.123` remains accepted/current while its formal proof attempt is excluded.

## MVP finalization rule

Bounded parallel release-set wave execution remains deferred post-MVP. After `v0.1.123.1` acceptance, the operator runs exactly one `pb ask continue` command for `v0.1.124` and one for `v0.1.125`. Both must emit passed canonical proof artifacts consecutively without an intervening repair.

## Historical continuity

Historical continuity: v0.1.111, v0.1.111.2, v0.1.111.3, v0.1.111.4, v0.1.111.5, v0.1.111.5.2, v0.1.112, v0.1.113, v0.1.114, v0.1.114.2, v0.1.115, v0.1.115.1, v0.1.116, v0.1.117, v0.1.117.1, v0.1.118, v0.1.118.1, v0.1.119, v0.1.120, v0.1.120.1.
