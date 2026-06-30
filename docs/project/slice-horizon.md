# Slice Horizon

## Rolling horizon authority

`docs/project/plan-state.json` is the machine-readable authority. This Markdown file mirrors the active horizon for human review.

| Version | Slice | Status | Scope | Out of scope |
|---|---|---|---|---|
| v0.1.103.3 | Passive auth-readiness runtime-client wiring repair | active | Wire passive auth readiness into the actual Promptbranch browser client used by the service | Project Source mutation, deployment, artifact adoption |
| v0.1.104 | Sandbox mutation verification and rollback evidence gate | planned_after_acceptance | Verify sandbox mutation result evidence and define rollback/stop gates | broader correction workflows, deployment |
| v0.1.105 | Sandbox correction promotion readiness check | planned | Decide whether sandbox-only correction evidence is ready for broader controlled workflows | deployment, autonomous promotion |
| v0.1.106 | Controlled correction promotion decision record | planned | Record whether correction workflows may move beyond sandbox fixtures | unapproved mutation, deployment |
| v0.1.107 | Controlled correction execution envelope design | planned | Define future execution envelope for controlled corrections without enabling repository-wide mutation | repository-wide mutation, deployment |

## Repair horizon rule

Repair releases must keep the active normal slice fixed, set `scope_advance_allowed=false`, and must not move the rolling horizon forward.
