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


## Active repair candidate — v0.1.125.2

- accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.124.zip` (`v0.1.124`)
- failed normal candidate retained as evidence: `chatgpt_claudecode_workflow-2_v0.1.125.zip`
- prior repair retained as failed full-validation evidence: `chatgpt_claudecode_workflow-2_v0.1.125.1.zip`
- active repair artifact: `chatgpt_claudecode_workflow-2_v0.1.125.2.zip`
- active repair slice: v0.1.125.2 — Version-independent authority-drift fixture repair
- next normal slice remains: `v0.1.125 — Canonical PB environment proof cycle 2 and final control-plane verdict`
- planned after repair acceptance: `v0.1.126 — Persistent whole-release ETA estimator`
- scope advancement: forbidden; repair only removes the stale version-specific authority test literal while preserving isolated compileall and cache-free repeatability
