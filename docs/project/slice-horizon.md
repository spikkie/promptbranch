## Active repair horizon

- `v0.1.127` — repair-required after two live ask completion deadlines.
- `v0.1.127.1 — Artifact-bound conversation provenance and successor ask routing` — repair-required after live same-project slug normalization failure.
- `v0.1.127.2.1 — Consolidated v0.1.127 closure and single-Python lifecycle repair` — active consolidated closure repair; no scope advancement.
- `v0.1.127.1.1.1.1 — Acceptance-path conversation provenance validator repair` — superseded before live by single-Python authority requirement.
- `v0.1.127.1.1.1 — Successor ask pin propagation and TESTED_GREEN route verification` — repair-required predecessor; live route proof passed, ACCEPTED blocked before mutation by undefined helper.
- `v0.1.127.1.1 — Canonical ChatGPT project identity for artifact conversation provenance` — repair-required predecessor; project identity fix retained.
- `v0.1.128` — planned after acceptance.

> v0.1.127 normal-slice authority: accepted/current is `v0.1.126.1.1.1.1.3`; `v0.1.127` is active; `v0.1.128` is planned after acceptance. Tool authoring does not grant execution authority.

# Rolling Slice Horizon

Documentation checkpoint: `PB-TOOL-AUTHORING-2026-08-09.1`

| Version | Mode | Status | System | Scope |
|---|---|---|---|---|
| v0.1.125.3.4.2 | repair | superseded | PB control plane | previous accepted control-plane checkpoint |
| v0.1.126 | normal | completed_via_repair | PB environment | persistent whole-release ETA estimator |
| v0.1.126.1.1.1.1.2 | repair | repair_required | PB environment | accepted-runtime guard live-proven; superseded by .3 |
| v0.1.126.1.1.1.1.3 | repair | accepted_current | PB environment | validation-Python authority repair and final v0.1.126 convergence |
| v0.1.127.2.1 | repair | active | PB environment | consolidated v0.1.127 tool-authoring + provenance + route + acceptance + single-Python closure |
| v0.1.128 | normal | planned_after_acceptance | PB environment | profile-aware timeouts, candidate recovery, summary consistency, policy freeze |
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


## Active normal candidate — v0.1.127

- accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.126.1.1.1.1.3.zip` (`v0.1.126.1.1.1.1.3`)
- active artifact: `chatgpt_claudecode_workflow-2_v0.1.127.zip`
- active slice: `v0.1.127 — Portable Promptbranch tool-authoring skill and export bundle`
- next planned after acceptance: `v0.1.128 — PB environment MVP hardening and freeze`
- authoring/export is proposal-only; release/adoption authority remains state-machine controlled.

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

## v0.1.128.1 repair horizon

`v0.1.128.1 — Single authority for Promptbranch release artifacts` is the active bounded repair on accepted/current `v0.1.128`. It does not advance normal scope. The next normal slice remains `v0.1.129 — External application pilot bootstrap` after the repair reaches FINAL_VERIFIED/current.


## v0.1.128.1.1 repair horizon

`v0.1.128.1.1 — Lifecycle resume, progress, diagnostics, and control-projection repair` is the active bounded repair on accepted/current `v0.1.128.1`. It fixes only wrapper retry-resume, live stderr progress/ETA, ask failure classification, and authoritative-current control projection. `v0.1.129 — External application pilot bootstrap` remains planned after acceptance.

## v0.1.128.1.1.1 repair horizon

`v0.1.128.1.1.1 — Post-adoption control-projection completeness repair` is the active bounded repair on adopted/current `v0.1.128.1.1`. It fixes only projection completeness and the shared projection-file contract. `v0.1.129 — External application pilot bootstrap` remains planned after acceptance; `v0.1.130 — Controlled external application change execution` remains planned after that.


## v0.1.128.1.1.1.1 repair horizon

`v0.1.128.1.1.1.1 — Fresh assistant-chain continuity repair` is the active bounded repair on adopted/current `v0.1.128.1.1`. It carries the construction-proven `.1.1.1` projection-completeness repair unchanged and fixes only response freshness continuity after a causally confirmed submit and observed generation. A freshly established assistant chain remains fresh across same-visible-count streaming updates even when its final deterministic text equals the historical baseline; stale baseline-identical text without the fresh-chain latch remains rejected. `v0.1.129 — External application pilot bootstrap` remains planned after acceptance.


## v0.1.128.1.1.1.1.1 repair horizon

`v0.1.128.1.1.1.1.1 — Task/message response-chain diagnostic repair` is the active bounded repair on adopted/current `v0.1.128.1.1`. It carries the `.1.1.1` projection repair and `v0.1.128.1.1.1.1` fresh assistant-chain repair unchanged. The only new scope is structured diagnostic logging/state capture for the `task_message_flow.ask` new-Project-chat timeout, including URL/conversation transition, freshness latch, candidate identity, completion predicates, and terminal timeout state. `v0.1.129 — External application pilot bootstrap` remains planned after acceptance.

## v0.1.128.2 — Promptbranch learning and skills completeness

Active normal PB-environment slice. Completes canonical onboarding for humans, ChatGPT Projects, Claude/coding agents, generic coding agents, and PB-aware agents through deterministic read-only learning/operator bundles. After acceptance, `v0.1.129 — External application pilot bootstrap` becomes active. Repair horizon rule remains unchanged: repair releases must not advance scope.


## v0.1.128.2.1 — Release smoke timeout auto-recovery repair

- Mode: repair.
- Baseline construction artifact: `v0.1.128.2`; accepted/current remains `v0.1.128.1.1.1.1.1`.
- Scope: preserve learning/skills completeness; make deterministic release smoke asks auto-recover supported transient service/response timeouts inside the initial lifecycle invocation.
- Fail-closed exclusions: authentication/challenge, 429/cooldown, exact-route mismatch, permission, and ambiguous submit causality are never converted into automatic success/retry.
- Next normal after repair: `v0.1.129 — External application pilot bootstrap`.
- Planned after next: `v0.1.130 — Controlled external application change execution`.

## v0.1.128.2.2 — Accepted-runtime baseline auto-reconciliation repair

- Mode: repair.
- System: Promptbranch environment/control plane.
- Scope: preserve v0.1.128.2 learning/skills and v0.1.128.2.1 smoke-timeout recovery; make the canonical lifecycle reconstruct missing/unhealthy/mismatched production baseline from the exact adopted registry artifact before candidate preparation.
- Authority: repository-scoped adopted artifact record + exact SHA/ZIP/VERSION proof; fail closed on ambiguity.
- After acceptance: `v0.1.129` becomes active; `v0.1.130` remains planned after acceptance.


## v0.1.128.2.3 — Project-scoped baseline registry authority repair

Repair only the baseline-recovery registry namespace: use tracked repo identity → canonical project-scoped artifact registry; preserve learning/skills, smoke-timeout recovery, and accepted-runtime reconstruction. Successful adoption advances directly to v0.1.129.


## v0.1.128.2.4 — Accepted-baseline exact-byte self-healing repair

Live `v0.1.128.2.3` resolved the canonical project-scoped registry but failed `accepted_baseline_artifact_invalid`. `v0.1.128.2.4` keeps `(repo_id, version, sha256)` as immutable accepted authority while making physical byte location recoverable: recorded path, canonical SHA object, PB artifact caches, exact repo-local copy, and operator Downloads are bounded candidate locations; every copy must match the registered SHA, safe ZIP integrity, and embedded baseline VERSION before use. An exact recovered copy restores canonical object storage. Wrong-SHA or unavailable bytes fail closed. Accepted baselines are verified for immutable integrity rather than re-judged by newer candidate hygiene policy. Accepted/current remains `v0.1.128.1.1.1.1.1`; next normal remains `v0.1.129`; `.129` is blocked until this repair reaches FINAL_VERIFIED/current.


## v0.1.128.2.5 — Authoritative baseline auto-resolution repair

The live v0.1.128.2.4 failure proved authoritative adopted/current is v0.1.128.2 while the launcher command still asserted the older v0.1.128.1.1.1.1.1 baseline. Fresh lifecycle attempts now resolve the project-scoped adopted/current baseline automatically; retries keep their durable attempt-bound baseline. An explicit baseline flag is assertion-only and fails closed on mismatch. This repair does not advance scope; v0.1.129 remains next normal.

## v0.1.128.2.6 — External-repository skill sync installation repair

Status: active repair. Scope: authoritative adopted/current skill source resolution; deterministic export/verify; target Git-repo preflight; staged all-or-rollback replacement; provenance; drift protection; dry-run; target validation; Git change report; no commit/push. Next normal: `v0.1.129`.

