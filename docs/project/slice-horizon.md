# Slice Horizon

## Rolling horizon authority

`docs/project/plan-state.json` is the machine-readable authority. This Markdown file mirrors the active horizon for human review.

| Version | Slice | Status | Scope | Out of scope |
|---|---|---|---|---|
| v0.1.103.10.9 | pb ask reuses held auth-ready browser session | active | Reuse the held standard-browser auth-readiness session for pb ask without Singleton* cleanup or competing browser contexts | Project Source mutation, host-CDP session manager, deployment, artifact adoption |
| v0.1.104 | Sandbox mutation verification and rollback evidence gate | planned_after_acceptance | Verify sandbox mutation result evidence and define rollback/stop gates | broader correction workflows, deployment |
| v0.1.105 | Sandbox correction promotion readiness check | planned | Decide whether sandbox-only correction evidence is ready for broader controlled workflows | deployment, autonomous promotion |
| v0.1.106 | Controlled correction promotion decision record | planned | Record whether correction workflows may move beyond sandbox fixtures | unapproved mutation, deployment |
| v0.1.107 | Controlled correction execution envelope design | planned | Define future execution envelope for controlled corrections without enabling repository-wide mutation | repository-wide mutation, deployment |

## Repair horizon rule

Repair releases must keep the active normal slice fixed, set `scope_advance_allowed=false`, and must not move the rolling horizon forward.


## v0.1.103.9 active repair horizon

`v0.1.103.9` is the active Docker parity repair horizon. It keeps the working standard browser mode, documents the clean logged-in profile test procedure, excludes browser profiles from Docker build context, and fixes safe no-artifact evidence export. Project Source mutation remains out of scope.

## v0.1.103.10.8 active repair horizon

`v0.1.103.10.8` is the active Docker parity repair horizon for the standard browser profile default. It remains candidate-only and keeps Project Source mutation out of scope.

## v0.1.103.10.9 active repair horizon

`v0.1.103.10.9` is the active standard-browser repair horizon after auth-readiness passed but `pb ask` opened a competing profile context. It remains candidate-only and keeps Project Source mutation plus v0.1.104.x host-CDP work out of scope.
