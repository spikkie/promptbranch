# Slice Horizon

## Rolling horizon authority

`docs/project/plan-state.json` is the machine-readable authority. This Markdown file mirrors the active horizon for human review.

| Version | Slice | Status | Scope | Out of scope |
|---|---|---|---|---|
| v0.1.103.10.17 | pbsa reuses held session for remembered overwrite removal | active | Keep one Docker browser owner for Project Source overwrite remove/add and avoid competing persistent contexts | direct API mutation without intent, host-CDP session manager, deployment, artifact adoption |
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


## v0.1.103.10.11 active repair horizon

`v0.1.103.10.11` is the active standard-browser repair horizon after `v0.1.103.10.10` still received Cloudflare immediately during auth-only validation. It adds Docker-originated visible browser profile bootstrap while keeping Project Source mutation and v0.1.104.x host-CDP work out of scope.

- status: active
- release_mode: repair
- scope: bootstrap the standard profile using visible Chrome launched from the Promptbranch Docker image and mounted as `/app/profile`
- version: v0.1.103.10.11
- slice: v0.1.103.10.11 — Docker-originated visible browser profile bootstrap

## v0.1.103.10.10 previous repair horizon

`v0.1.103.10.10` is the active standard-browser repair horizon after `v0.1.103.10.9` proved held-session reuse but still navigated to a Cloudflare-prone project conversation URL before sending. It remains candidate-only and keeps Project Source mutation plus v0.1.104.x host-CDP work out of scope.


## Active repair — v0.1.103.10.12

`v0.1.103.10.12 — pb ask preserves current project conversation scope` remains inside the standard browser repair line and does not advance v0.1.104.


## Active repair — v0.1.103.10.13

`v0.1.103.10.13 — guarded pbsa Project Source mutation intent` remains inside the standard browser repair line and does not advance v0.1.104.

- status: active
- release_mode: repair
- scope: allow explicit CLI source-add mutation only after Docker browser auth/profile preflight passes
- version: v0.1.103.10.13
- slice: v0.1.103.10.13 — guarded pbsa Project Source mutation intent

## Active repair — v0.1.103.10.15

`v0.1.103.10.15 — pbsa preserves Project Sources route before Add source lookup` remains inside the standard browser repair line and does not advance v0.1.104.

- status: active
- release_mode: repair
- scope: reuse compatible held auth-readiness session during Project Source mutation preflight and upload
- version: v0.1.103.10.15
- slice: v0.1.103.10.15 — pbsa preserves Project Sources route before Add source lookup


## Active repair — v0.1.103.10.19

`v0.1.103.10.19 — install-safe pb test api module runner`: add a rerunnable sequential API coverage command under `pb test api`; keep destructive endpoint behavior skipped/guarded by default.

## Active repair — v0.1.103.10.19

`v0.1.103.10.19 — install-safe pb test api module runner`: package the API coverage runner as an installed module and invoke it through `python -m` from `pb test api`.

## Active repair — v0.1.103.10.21

`v0.1.103.10.21 — pb test api classification cleanup`: make API coverage default to serial browser checks with no held auth-readiness session between unrelated endpoints; classify held-profile conflicts as `browser_profile_busy`.
## Active repair — v0.1.103.10.21

`v0.1.103.10.21 — pb test api classification cleanup`: narrow API coverage classification logic so passed/clear responses do not carry misleading failure classifications. No browser/session architecture changes.

## Active repair — v0.1.103.10.37

`v0.1.103.10.37 — missing live seed profile is non-blocking for run-all release validation`: enforce response-body semantic success checks in the API coverage runner; no browser/session architecture changes.


## Active repair slice — v0.1.103.10.37

`v0.1.103.10.37 — missing live seed profile is non-blocking for run-all release validation` adds a `pb test api` held-session preflight that detects an active held auth-readiness session across default, project, and conversation scopes; without `--reuse-held-session`, it fails early with `preflight.browser_profile_busy=true` instead of running doomed browser-owning endpoint calls. No browser/session architecture changes.

## Active repair slice — v0.1.103.10.37

`v0.1.103.10.37 — missing live seed profile is non-blocking for run-all release validation` remains inside the `v0.1.103.10.x` repair line and does not advance browser/session architecture.

Control-surface active slice token: v0.1.103.10.37 — release-control auth bootstrap accepts project-page readiness for source-add preflight
