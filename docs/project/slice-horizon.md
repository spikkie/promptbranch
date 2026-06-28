# Slice Horizon

## Rolling horizon authority

`docs/project/plan-state.json` is the machine-readable authority. This Markdown file mirrors the active horizon for human review.

| Version | Slice | Status | Scope | Out of scope |
|---|---|---|---|---|
| v0.1.102 | Correction-plan generation without file mutation | active | Produce bounded correction-plan evidence from diagnosis results without writing files | file writes, retries, deployment |
| v0.1.103 | First controlled file mutation in sandboxed fixture only | planned_after_acceptance | Perform first mutation only inside explicit sandbox fixture with before/after evidence | real repo mutation, Project Source mutation, deployment |
| v0.1.104 | Sandbox mutation verification and rollback evidence gate | planned | Verify sandbox mutation result evidence and define rollback/stop gates | broader correction workflows, deployment |
| v0.1.105 | Sandbox correction promotion readiness check | planned | Decide whether sandbox-only correction evidence is ready for broader controlled workflows | deployment, autonomous promotion |
| v0.1.106 | Controlled correction promotion decision record | planned | Record whether correction workflows may move beyond sandbox fixtures | unapproved mutation, deployment |

## Repair horizon rule

Repair releases must keep the active normal slice fixed, set `scope_advance_allowed=false`, and must not move the rolling horizon forward.
