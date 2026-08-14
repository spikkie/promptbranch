# v0.1.129 external application-development MVP bootstrap

The active normal slice begins the external application-development MVP without granting mutation authority. The first pilot is `k8s-game-mvp` in a repository separate from Promptbranch. This slice establishes only the target, architecture, Definition of Done, deterministic test declaration, and read-only execution plan. Application mutation remains forbidden until the controlled-change slice.

## Active closure repair — v0.1.127.2.1

Consolidated v0.1.127 closure from accepted/current `v0.1.126.1.1.1.1.3`: portable tool authoring, immutable conversation provenance, exact executed ask routing, acceptance provenance, and one exact launcher-Python authority are carried into one canonical candidate. No external-application scope advances; v0.1.127 closes only at live `FINAL_VERIFIED` plus scoped current alignment.

> v0.1.127 normal-slice authority: accepted/current is `v0.1.126.1.1.1.1.3`. The active scope is portable deterministic tool authoring/export with explicit proposal-only authority; external application development remains out of scope.

# MVP

## MVP name

```text
Promptbranch controlled ChatGPT Project workflow MVP
```

## MVP goal

```text
Promptbranch provides a safe, repeatable control-plane workflow around ChatGPT Projects: workspace/task/source/artifact state is explicit, LLM output remains proposal-only, release artifacts are verified before adoption, and each next release continues from the accepted baseline.
```

## Primary user/operator

```text
Operator/developer using Promptbranch as a CLI-driven workflow shell for ChatGPT Projects and ZIP-based software releases.
```

## Success signal

```text
The operator can continue from the accepted baseline, request a narrow release slice, receive a candidate ZIP, verify it, install/adopt it only after validation, and continue the next slice from the newly accepted baseline without relying on remembered state.
```

## In scope

- Workspace, task, source, and artifact state remain separate.
- Backend-first reads and transactional write verification remain the reliability model.
- Protocol-aware ask/reply, artifact intake, candidate verification, and guarded adoption remain the release safety model.
- Artifact Guardian validates candidate ZIP structure before release handoff; guard-passed remains separate from accepted/current adoption.
- JSON orchestration/grill events remain proposal-only until Promptbranch validates and records accepted events.
- Native release lifecycle work advances through read-only diagnostics and controlled prechecks before mutating install/adopt behavior.
- Project continuation is documented through `docs/project/`.

## Out of scope

- Autonomous repository editing.
- Autonomous Project Source overwrite.
- Automatic artifact adoption from assistant prose.
- Write-capable MCP execution from model proposals.
- Local/Ollama critical-path orchestration provider without a passing bakeoff and ADR.
- Broad shell execution.
- Kubernetes game implementation or deployment as part of this migration slice.

## Non-goals

- Literal Claude Code parity.
- Treating ChatGPT as the execution authority.
- Replacing all repo-local release scripts in one step.
- Turning documentation migration into MVP completion.

## Critical assumptions

- Accepted baseline evidence from `pb artifact current --json` is authoritative.
- ZIP artifacts are immutable once accepted.
- A candidate ZIP is not accepted/current until runtime, state artifact, state source, registry current, and consistency align.
- Existing planning documents contain useful history and must be preserved.

## Main risks

- Baseline drift if future work continues from a candidate or stale version.
- Authority drift if assistant proposals are treated as accepted workflow state.
- Documentation drift if `docs/project/` is not kept current after each release.
- Scope creep from read-only lifecycle diagnostics into mutating lifecycle behavior before guards are complete.

## MVP boundaries

```text
This MVP is complete only when the Definition of Done in docs/project/definition-of-done.md is satisfied with evidence.
```

## v0.1.86 k8s-game reconciliation note

The Kubernetes game remains a controlled test vehicle for the JSON orchestration state MVP. It is not yet an implementation target in this release.

`v0.1.86` reconciles the project control surface and orchestration design docs against accepted/current `chatgpt_claudecode_workflow-2_v0.1.85.zip`. Game implementation, Docker image changes, Kubernetes manifest application, Helm use, cluster mutation, Project Source mutation, artifact adoption/current behavior changes, and accepted-event ledger writes are out of scope for this slice.


## MVP-0 / MVP-1 framing

```text
MVP-0:
  Promptbranch release/artifact/control-plane foundation.

MVP-1:
  Automatic multi-step plan execution loop, starting with state-only walkthrough.
```

`v0.1.91.10` completed the MVP-0 foundation proof: candidate ZIP install/import, service bootstrap, Project Source add, full validation, run-all progress, Artifact Guardian, adopt-after-validation, and artifact-current alignment.

`v0.1.92` opened MVP-1 with the smallest safe step: `pb loop run --state-only` walks the existing dry-run loop state machine and prints only state transitions.

`v0.1.93` advances MVP-1 from state names to a planned-action walkthrough: `pb loop run --planned-actions` prints what each state would do and which gate would validate it, while still performing no commands, tests, deployment, Project Source mutation, artifact adoption, or ChatGPT Project deletion. The Kubernetes game remains the first future acceptance scenario, not an implementation target in this slice.

`v0.1.93.1` is a repair-only continuation of the `v0.1.93` MVP-1 planned-action slice. It does not advance MVP-1 scope; it isolates offline scheduler/source release-validation nodeids from direct live browser/service/profile environment state.

`v0.1.94.1` is accepted/current repair evidence for the first controlled read-only loop execution step and Project Source capacity-prune identity guard.

`v0.1.95` adds a compact read-only evidence report for MVP-1 loop execution preflight. The loop still executes no commands, mutates no files, performs no Kubernetes/deployment action, mutates no Project Sources, adopts no artifacts, and deletes no ChatGPT Projects.

`v0.1.96` keeps Project Source capacity manageable for multi-repo Projects by retaining only the latest five generated release ZIP sources per release family/repository. It does not delete documentation or non-generated Project Sources and does not change loop execution, artifact adoption, deployment, Kubernetes, or ChatGPT Project deletion behavior.


## 2026-08-06 MVP layer clarification

The accepted `v0.1.124` checkpoint completes the native local candidate/artifact lifecycle for Promptbranch itself. It does not complete the external application-development MVP.

MVP layer targets:

- PB control-plane proof: `v0.1.125`;
- PB environment hardening/freeze: `v0.1.128`;
- first external application-development MVP: `v0.1.132`;
- non-production deployment MVP: `v0.1.133`;
- reusable application platform: `v0.1.134`.

The first external application mutation is forbidden before the `v0.1.130` execution-envelope and rollback gate.


## Active normal candidate — v0.1.127

- accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.126.1.1.1.1.3.zip` (`v0.1.126.1.1.1.1.3`)
- active artifact: `chatgpt_claudecode_workflow-2_v0.1.127.zip`
- scope: tracked `promptbranch-tool-authoring` skill, machine-readable deterministic tool specification, fail-closed semantic validation, and byte-reproducible export bundle
- portable targets: one self-contained `PROJECT_SOURCE.md` for ChatGPT Project Sources plus `SKILL.md`/`AGENTS.md`/schema/example for coding agents
- authority: authoring is proposal-only; validation does not register, implement, execute, mutate, release, publish, or adopt a tool
- next planned after acceptance: `v0.1.128 — PB environment MVP hardening and freeze`

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
- no backward-compatibility path for superseded post-adoption candidate-liveness semantics
- next normal slice: `v0.1.126 — Persistent whole-release ETA estimator`

## Active normal candidate — v0.1.126

- accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.125.3.4.2.zip` (`v0.1.125.3.4.2`)
- active artifact: `chatgpt_claudecode_workflow-2_v0.1.126.zip`
- scope: persistent whole-release ETA, expected finish, evidence confidence/provenance, and advisory timeout-risk diagnostics
- authority: ETA cannot change canonical test, acceptance, adoption, production-promotion, rollback, or `FINAL_VERIFIED` results
- compatibility: no legacy PB ETA/state compatibility layer is retained; canonical release-attempt evidence seeds the new model
- next planned after acceptance: `v0.1.127 — Portable Promptbranch tool-authoring skill and export bundle`


## Active repair candidate — v0.1.126.1.1.1.1.2

- repair input candidate: `v0.1.126.1.1.1.1.1`
- accepted/current baseline: `v0.1.125.3.4.2`
- scope: strengthen the `RUNTIME_PREPARED` accepted-runtime precondition and preservation proof; do not advance the normal ETA slice
- authority: missing/unhealthy/mismatched production blocks retryably; candidate preparation may not auto-recover production
- completion: requires live canonical lifecycle through `FINAL_VERIFIED` before any accepted/current claim


## Active repair candidate — v0.1.126.1.1.1.1.3

- repair input candidate: `v0.1.126.1.1.1.1.2`
- accepted/current baseline: `v0.1.125.3.4.2`
- scope: preserve explicit candidate validation-Python authority through release-contract environment sanitization; do not advance the normal ETA slice
- proof basis: `v0.1.126.1.1.1.1.2` full live candidate suite passed 53/53; publication preflight failed only because foreign pytest 8.4.2 replaced candidate pytest 9.0.2
- completion: requires live canonical lifecycle through `FINAL_VERIFIED` before any accepted/current claim


## Active repair candidate — v0.1.127.1.1.1

- repair input candidate: `v0.1.127.1.1`
- accepted/current baseline: `v0.1.126.1.1.1.1.3`
- scope: propagate `--ask-conversation-url` through `pb test full` into browser execution and make `TESTED_GREEN` require exact executed ask URL/conversation ID evidence
- authority: a generic green suite or a flag present only in the subprocess argv is insufficient; route proof must come from the saved browser report
- preserved: `.127.1` provenance semantics, `.127.1.1` project-identity normalization, source/task isolation, response-completion behavior, and the `v0.1.127` tool-authoring product scope
- completion: requires fresh live route proof for conversation ID `6a78783b-3e00-83eb-8dc1-1e814fcf2a59`, then canonical lifecycle through `FINAL_VERIFIED` before any accepted/current claim
