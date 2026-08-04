# Slice Horizon

## Current rolling horizon

| Version | Slice | Status | Release mode | Scope |
|---|---|---|---|---|
| v0.1.123 | Canonical MVP proof cycle attempt | accepted_historical_proof_not_counted | normal | release/adoption passed, but chronological intake was absent |
| v0.1.123.2.1 | Project authority URL alias reconciliation | failed_pre_validation | repair | project join fixed; caller-side literal verification still failed |
| v0.1.123.2.2 | Release-control post-join Project alias verification | accepted_current | repair | caller and join compare immutable Project UUID aliases |
| v0.1.123.2.3 | Operation-scoped response waiting | active | repair | confirmed-submit guardrail cursor and nested timeout budget |
| v0.1.124 | Canonical MVP proof cycle 1 | planned_after_acceptance | normal | first complete pinned one-command proof |
| v0.1.125 | Canonical MVP proof cycle 2 and final verdict | planned | normal | second consecutive pinned one-command proof |

## Independence rule

Promptbranch and `promptbranch-method` develop independently. Method releases remain compatible with the accepted runtime contract `Promptbranch >= v0.1.116`; adoption of the generic release pipeline remains an explicit project decision.

## Repair horizon rule

Repair releases must not advance scope. `v0.1.123.2.3` can repair response-wait causality and timeout nesting but cannot count as a normal proof cycle. Accepted/current remains `v0.1.123.2.2` until strict adoption evidence advances it.

## MVP finalization rule

After `v0.1.123.2.3` acceptance, the operator runs one explicitly pinned `pb ask continue` command for `v0.1.124` and one for `v0.1.125`. Both must pass consecutively without an intervening repair.

## Historical continuity

Historical continuity: v0.1.111, v0.1.111.2, v0.1.111.3, v0.1.111.4, v0.1.111.5, v0.1.111.5.2, v0.1.112, v0.1.113, v0.1.114, v0.1.114.2, v0.1.115, v0.1.115.1, v0.1.116, v0.1.117, v0.1.117.1, v0.1.118, v0.1.118.1, v0.1.119, v0.1.120, v0.1.120.1.
