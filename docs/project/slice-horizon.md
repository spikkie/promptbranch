# Slice Horizon

## Current rolling horizon

| Version | Slice | Status | Release mode | Scope |
|---|---|---|---|---|
| v0.1.122.1 | MVP proof finalizer fail-closed evidence repair | accepted_historical | repair | project-level current parsing, exact SHA binding, preflight ordering, and truthful exit status |
| v0.1.123 | Canonical MVP proof cycle attempt | accepted_historical_proof_not_counted | normal | release/adoption passed, but chronological intake was absent |
| v0.1.123.1 | Complete proof lifecycle ownership in `pb ask` | accepted_current | repair | one-command exact correlation and fail-closed sequencing |
| v0.1.123.2 | Explicit conversation pinning | active | repair | authoritative CLI conversation URL across candidate Ask, intake, and continuation |
| v0.1.124 | Canonical MVP proof cycle 1 | planned_after_acceptance | normal | first complete pinned one-command proof |
| v0.1.125 | Canonical MVP proof cycle 2 and final verdict | planned | normal | second consecutive pinned one-command proof |

## Independence rule

Promptbranch and `promptbranch-method` develop independently. Method releases remain compatible with the accepted runtime contract `Promptbranch >= v0.1.116`; adoption of the generic release pipeline remains an explicit project decision.

## Repair horizon rule

Repair releases must not advance scope. `v0.1.123.2` can pin conversation identity but cannot count as a normal proof cycle. Accepted/current remains `v0.1.123.1` until strict adoption evidence advances it.

## MVP finalization rule

After `v0.1.123.2` acceptance, the operator runs one explicitly pinned `pb ask continue` command for `v0.1.124` and one for `v0.1.125`. Both must pass consecutively without an intervening repair.

## Historical continuity

Historical continuity: v0.1.111, v0.1.111.2, v0.1.111.3, v0.1.111.4, v0.1.111.5, v0.1.111.5.2, v0.1.112, v0.1.113, v0.1.114, v0.1.114.2, v0.1.115, v0.1.115.1, v0.1.116, v0.1.117, v0.1.117.1, v0.1.118, v0.1.118.1, v0.1.119, v0.1.120, v0.1.120.1.
