# v0.1.129 external application pilot architecture boundary

The active architecture introduces no second Promptbranch control plane. `promptbranch_application_pilot` is a read-only bridge from System A to a separate System B repository. System A may validate and plan; System B retains independent product target, version, architecture, tests, artifact, acceptance, and later deployment authority.

Fixed pilot invariant: the target repository must differ from the Promptbranch repository, and the bootstrap planner may not run Git or mutate either repository. The application PBAI-001 declaration is proposed as an application-owned file, not inherited from Promptbranch. Controlled mutation begins only after explicit later authority and rollback evidence.

# Project Architecture Principles

## Purpose

Promptbranch is designed as a controlled problem-solving loop:

target → understand → plan → act safely → verify → diagnose → correct → retest → stop/adopt/deploy only when explicitly allowed.

This document separates fixed architecture invariants from adaptive design choices. Design remains a process, but the process must not drift away from the product goal or the accepted/current baseline.

## Fixed architecture invariants

These invariants are fixed for the current MVP line unless a later release records an explicit architecture decision in `docs/project/decisions.md` and updates `docs/project/plan-state.json`.

1. Artifact-first baseline continuity
   - Every release starts from the latest accepted/current artifact.
   - Normal releases must not build from arbitrary local trees, older ZIPs, or remembered versions.
   - Repair releases build from the failed candidate or latest accepted repair line as declared by the repair note.

2. Control surface is authoritative
   - `docs/project/plan-state.json` is the machine-readable authority.
   - Markdown docs explain and cross-check that authority.
   - Conversation memory can provide context but must not override repo state.

3. Exactly one active normal slice
   - The control surface must name one active normal slice.
   - Repairs belong to that slice and must not advance scope.

4. Repair releases must not advance scope
   - Repairs may fix validation, packaging, stale control surface, release-control, or defects inside the intended slice.
   - Repairs may not introduce the next feature slice.

5. Actuation is layered and gated
   - Evidence-only behavior comes before execution.
   - Read-only execution comes before correction planning.
   - Correction planning comes before file mutation.
   - File mutation comes before artifact adoption or deployment.

6. ChatGPT Project deletion remains frozen
   - No release may re-enable whole-Project deletion without a specific secure delete protocol decision and validation.

7. Loop execution cannot silently mutate release surfaces
   - Project Source mutation and artifact adoption are explicit release operations.
   - Loop execution may not mutate Project Sources or adopt artifacts unless a slice explicitly permits and validates it.

8. Repo-relative paths only
   - Architecture docs, policy examples, validators, and fixtures must use repo-relative paths.
   - Packaging wrapper-folder paths are not valid repo references.

## Adaptive design space

The following may change through normal slices when evidence shows a better approach:

- exact CLI option spelling
- browser selector strategy
- timeout/retry policy
- validation fixture choice
- command allowlist shape
- JSON schema details, when migration is documented
- test grouping, when release-control semantics remain equivalent

## Slice derivation inputs

Future slices are derived from:

- main product goal
- current MVP stage
- architecture invariants
- Definition of Done
- latest accepted/current baseline
- known blockers and repair history
- smallest testable next capability
- operational risk

## Replanning rule

A normal release may replan the rolling horizon only when it records why in `docs/project/decisions.md`, updates `docs/project/slice-horizon.md`, and updates `docs/project/plan-state.json`.

A repair release may not replan the active normal slice. If a repair reveals that the horizon is wrong, it must record evidence and leave the horizon change to the next normal release.

## PBAI-001 application architecture invariant

`.promptbranch-ai.json` owns the tracked AI application architecture declaration. A full application declares ten layers: instructions/policy, runtime actors, skills, tools, validators, knowledge/context, state/contracts, evidence/records, controller/authority, and lifecycle/recovery.

Promptbranch is the generic `runtime_application`. PB domain modules delegate the exact generic-runtime capability set to Promptbranch and own only domain behavior. Declaration and structural validation are read-only and fail closed. The reported proof level is monotonic and evidence-bound: declaration and structural evidence cannot imply registry, executable, or operational completion.


## PBAI registry proof

The declaration owns architecture shape; `.promptbranch/ai-registry.json` owns stable AI object identities and references. Registry validation is static and read-only: it parses Python AST, Skill frontmatter, JSON schemas, capability ownership, and controller boundaries without importing project modules or executing declared commands.


## 2026-08-06 system boundary and roadmap

Promptbranch architecture now explicitly distinguishes:

```text
System A — Promptbranch environment/control plane
System B — external application/tool developed using PB
```

System A owns orchestration, state, policy, evidence, browser integration, candidate handling, and PB release authority. System B owns its own product architecture, source, tests, artifact, accepted/current baseline, and deployment authority.

The release boundary is:

- `v0.1.125`–`v0.1.128`: complete and harden System A;
- `v0.1.129`: read-only System B bootstrap;
- `v0.1.130`–`v0.1.132`: controlled System B change/test/release MVP;
- `v0.1.133`: non-production deployment proof;
- `v0.1.134`: reusable application workflow.

No PB environment test may be treated as evidence that an application works. No external application candidate may mutate the PB artifact registry or accepted/current state.

See `docs/project/pb-environment-vs-application-development.md` and `docs/project/pb-mvp-roadmap-v0.1.124.md`.

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


## Canonical runtime-verification lifecycle

The isolated candidate runtime is ephemeral. `RUNTIME_PREPARED` requires live candidate health only before adoption. Once `ADOPTED_CURRENT` promotes the exact tested image and removes candidate containers, historical candidate validity is verified from immutable checkpoint evidence while current runtime validity is verified against the live authoritative service on port 8000. Superseded post-adoption candidate-liveness semantics are removed rather than preserved for backward compatibility.


## Active repair candidate — v0.1.125.3.4.2

- accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.125.3.4.1.zip` (`v0.1.125.3.4.1`)
- active repair artifact: `chatgpt_claudecode_workflow-2_v0.1.125.3.4.2.zip`
- active repair slice: v0.1.125.3.4.2 — Post-adoption historical verification and final convergence
- no backward-compatibility path for superseded post-adoption candidate-liveness semantics
- next normal slice: `v0.1.126 — Persistent whole-release ETA estimator`

## v0.1.126 whole-release ETA architecture

The canonical release state machine remains the sole lifecycle authority. `promptbranch_release_eta.py` consumes canonical transition evidence and writes a separate advisory history/snapshot surface keyed by profile, phase, transport, and step. The estimator may report remaining duration, expected finish, confidence/provenance, and timeout risk, but it cannot alter transition guards or verdicts.

The architecture deliberately does not retain compatibility paths for superseded PB timing models. Canonical `release_attempts_v2` evidence is the only historical seed authority for the new whole-release estimator. This preserves the controlled problem-solving loop, Fixed architecture invariants, Repair releases must not advance scope, and the PBAI-001 application architecture invariant.

## v0.1.126.1.1 canonical release-source identity

All release-source identity checks consume the shared `promptbranch_source_fingerprint` implementation. The canonical digest binds deterministic relative path, executable bit, and content digest while excluding VCS/profile/generated/transient state. Docker no longer maintains a separate release identity algorithm. A blocked retryable lifecycle has no active wall-clock ETA; the estimator reports only advisory work remaining after resume.

## v0.1.126.1.1.1 Project Source text readiness

Text-source mutation uses the body editor as the value authority. Save readiness is a bounded state machine: exact body/title value proof, controlled event stabilization, save-button re-resolution, then structured failure. Zero-request recovery is permitted only after authoritative source-surface reconciliation and at most one retry.

## v0.1.126.1.1.1.1 ask deadline authority

Docker-backed integration asks have one explicit outer service budget. The HTTP client uses that budget, `/v1/ask` owns an earlier internal deadline, and the canonical test consumes the structured ask result. A transport `ReadTimeout` is evidence of a service-client boundary failure, never permission to resubmit.

## v0.1.126.1.1.1.1.1 runtime fingerprint publication authority

Runtime source identity has one persisted authority: the attempt-local runtime checkpoint. `RUNTIME_PREPARED` carries an exact projection for observability. Publication may proceed only when checkpoint and projection are both present and identical; worktree and committed-tree guards resolve the fingerprint through the same accessor.
