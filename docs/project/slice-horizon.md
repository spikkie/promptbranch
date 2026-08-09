> v0.1.126.1.1.1.1.3 repair authority: built from immutable v0.1.126.1.1.1.1.2; accepted/current remains v0.1.125.3.4.2. Repairs release-validation Python authority propagation through the sanitized publication environment; no scope advance.


# Rolling Slice Horizon

Documentation checkpoint: `PB-ETA-2026-08-07.1`

| Version | Mode | Status | System | Scope |
|---|---|---|---|---|
| v0.1.125.3.4.1 | repair | superseded | PB control plane | operational promotion checkpoint superseded by final convergence repair |
| v0.1.125.3.4.2 | repair | accepted_current | PB control plane | post-adoption historical verification and final convergence |
| v0.1.126.1.1.1 | repair | repair_required | PB environment | text-source body authority and bounded recovery; live full flow later blocked at ask timeout |
| v0.1.126.1.1.1.1 | repair | repair_required | PB environment | ask repair passed 53/53; publication blocked by missing runtime fingerprint projection |
| v0.1.126.1.1.1.1.1 | repair | repair_required | PB environment | publication fingerprint repair; live runtime evidence exposed missing-production preservation defect |
| v0.1.126.1.1.1.1.2 | repair | repair_required | PB environment | accepted-runtime guard live-proven; publication environment authority defect remains |
| v0.1.126.1.1.1.1.3 | repair | active | PB environment | preserve explicit candidate validation Python through sanitized publication execution |
| v0.1.127 | normal | planned_after_acceptance | PB environment | portable `promptbranch-tool-authoring` skill and export bundle |
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


## Active normal candidate — v0.1.126

- accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.125.3.4.2.zip` (`v0.1.125.3.4.2`)
- active artifact: `chatgpt_claudecode_workflow-2_v0.1.126.zip`
- active slice: `v0.1.126 — Persistent whole-release ETA estimator`
- next planned after acceptance: `v0.1.127 — Portable Promptbranch tool-authoring skill and export bundle`
- ETA is advisory only; validation and adoption remain fail-closed and state-machine authoritative.

## Repair horizon rule

A repair may correct only the active slice. A PB-environment repair cannot introduce external application mutation. An external-application repair cannot mutate or adopt the PB control-plane artifact.

## Independence rule

Promptbranch, `promptbranch-method`, and every application repository retain independent version, artifact, candidate, acceptance, and deployment authority.

## Active repair candidate — v0.1.125.3.3

- accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.125.3.2.zip` (`v0.1.125.3.2`)
- accepted baseline SHA-256: `c6e6617a22b526b6bb3ae7f65274ce6edd75898ce926e24bda204bfc8b68504f`
- active repair artifact: `chatgpt_claudecode_workflow-2_v0.1.125.3.3.zip`
- active repair slice: v0.1.125.3.3 — Acceptance/adoption transactional reconciliation
- next normal slice: `v0.1.126 — Persistent whole-release ETA estimator`
- planned after repair acceptance: `v0.1.126 — Persistent whole-release ETA estimator`
- scope advancement: forbidden; repair only fixes action-aware acceptance/current result selection, post-side-effect reconciliation, idempotent stale-attempt recovery, and final state convergence


## Active repair candidate — v0.1.125.3.4.1

- control-plane accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.125.3.3.zip` (`v0.1.125.3.3`)
- active repair artifact: `chatgpt_claudecode_workflow-2_v0.1.125.3.4.1.zip`
- active repair slice: v0.1.125.3.4.1 — Candidate-test retry isolation and authoritative runtime final convergence
- observed pre-repair authoritative Docker service: `promptbranch-service:0.1.125.2` on port `8000`
- required promotion: retag the exact tested candidate image as `promptbranch-service:0.1.125.3.4.1`, recreate only the canonical `chatgpt_claudecode_workflow` service on port `8000`, and require live health plus version/SHA/attempt labels to match before `ADOPTED_CURRENT`
- rollback: restore the previously healthy production image when promotion fails; keep the release attempt retryable
- cleanup: remove isolated `pb-candidate-*` service containers only after authoritative runtime convergence
- `FINAL_VERIFIED`: must independently re-probe the live port-8000 service and fail on runtime drift
- next normal slice remains `v0.1.126 — Persistent whole-release ETA estimator`; repair scope does not advance application work


## Active repair candidate — v0.1.125.3.4.2

- accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.125.3.4.1.zip` (`v0.1.125.3.4.1`)
- active repair artifact: `chatgpt_claudecode_workflow-2_v0.1.125.3.4.2.zip`
- active repair slice: v0.1.125.3.4.2 — Post-adoption historical verification and final convergence
- old post-adoption live-candidate verification is replaced, not retained as a compatibility mode
- next normal slice remains `v0.1.126 — Persistent whole-release ETA estimator`
