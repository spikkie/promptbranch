# Rolling Slice Horizon

Documentation checkpoint: `PB-DOC-2026-08-06.1`

| Version | Mode | Status | System | Scope |
|---|---|---|---|---|
| v0.1.124 | normal | accepted_current | PB environment | accepted local candidate/artifact lifecycle checkpoint |
| v0.1.125 | normal | active | PB environment | second canonical proof cycle and final control-plane verdict |
| v0.1.126 | normal | planned | PB environment | persistent whole-release ETA and expected-finish estimator |
| v0.1.127 | normal | planned | PB environment | portable `promptbranch-tool-authoring` skill and export bundle |
| v0.1.128 | normal | planned | PB environment | profile-aware timeouts, candidate recovery, summary consistency, policy freeze |
| v0.1.129 | normal | planned | external application | pilot repository bootstrap, target, architecture, DoD, read-only slice plan |
| v0.1.130 | normal | planned | external application | human-authorized bounded source change and rollback evidence |
| v0.1.131 | normal | planned | external application | application tests, diagnosis, smallest correction, bounded retest |
| v0.1.132 | normal | planned | external application | app artifact candidate, verification, testing, explicit acceptance |
| v0.1.133 | normal | planned | external application | non-production deployment and post-deployment verification |
| v0.1.134 | normal | planned | PB application platform | reusable templates, domain modules, multi-repo/release-set generalization |

## Boundary rule

`v0.1.125` through `v0.1.128` continue development and validation of Promptbranch itself. `v0.1.129` begins the external application track, but remains read-only. The first external application mutation is not authorized before `v0.1.130`.

## Preserved roadmap rule

The previously defined purposes of `v0.1.125`, `v0.1.126`, and `v0.1.127` are preserved. The new plan appends `v0.1.128` through `v0.1.134`; it does not reorder or replace those releases.

## Repair horizon rule

A repair may correct only the active slice. A PB-environment repair cannot introduce external application mutation. An external-application repair cannot mutate or adopt the PB control-plane artifact.

## Independence rule

Promptbranch, `promptbranch-method`, and every application repository retain independent version, artifact, candidate, acceptance, and deployment authority.


## Active repair candidate — v0.1.125.2

- accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.124.zip` (`v0.1.124`)
- failed normal candidate retained as evidence: `chatgpt_claudecode_workflow-2_v0.1.125.zip`
- prior repair retained as failed full-validation evidence: `chatgpt_claudecode_workflow-2_v0.1.125.1.zip`
- active repair artifact: `chatgpt_claudecode_workflow-2_v0.1.125.2.zip`
- active repair slice: v0.1.125.2 — Version-independent authority-drift fixture repair
- next normal slice remains: `v0.1.125 — Canonical PB environment proof cycle 2 and final control-plane verdict`
- planned after repair acceptance: `v0.1.126 — Persistent whole-release ETA estimator`
- scope advancement: forbidden; repair only removes the stale version-specific authority test literal while preserving isolated compileall and cache-free repeatability
