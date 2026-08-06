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


## Active repair candidate — v0.1.125.1

- accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.124.zip` (`v0.1.124`)
- failed normal candidate retained as evidence: `chatgpt_claudecode_workflow-2_v0.1.125.zip`
- active repair artifact: `chatgpt_claudecode_workflow-2_v0.1.125.1.zip`
- active repair slice: v0.1.125.1 — Isolated compileall and repeatable template-snapshot validation repair
- next normal slice remains: `v0.1.125 — Canonical PB environment proof cycle 2 and final control-plane verdict`
- planned after repair acceptance: `v0.1.126 — Persistent whole-release ETA estimator`
- scope advancement: forbidden; repair only isolates compileall bytecode and restores repeatable cache-free validation
