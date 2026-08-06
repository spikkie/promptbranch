# Promptbranch PB MVP status and extended release roadmap

Documentation release: `PB-DOC-2026-08-06.1`  
Date: `2026-08-06`  
Accepted/current artifact baseline: `chatgpt_claudecode_workflow-2_v0.1.124.zip`  
Accepted SHA-256: `e4202f93b3e711a591d4c41be81fb85d97ce177e0fec41431fc9f1715e6cb3de`

## Executive position

Promptbranch has reached a **proven local candidate/artifact lifecycle** for its own environment. The next work is not yet general application development. First, the PB environment must complete one more repeatable proof and then be hardened into an unambiguous control-plane contract. Only after that boundary is frozen do we start the first external application pilot.

## Milestone model

| Milestone | Meaning | Planned completion |
|---|---|---|
| CP-PROOF | Two repeatable PB environment candidate lifecycle proofs | `v0.1.125` |
| CP-HARDENED | PB environment contract is repeatable without manual recovery | `v0.1.128` |
| APP-MVP | PB drives one external app through change, tests, candidate, and acceptance | `v0.1.132` |
| DEPLOY-MVP | Explicit non-production deployment and post-deploy verification | `v0.1.133` |
| APP-PLATFORM | Reusable templates and multi-repository application workflow | `v0.1.134` |

## Preserved existing roadmap

### v0.1.125 — Canonical PB environment proof cycle 2 and final control-plane verdict

This remains the next normal release. It must not become an application feature release.

In scope:

1. Start from accepted/current `v0.1.124`.
2. Run one explicitly pinned release-candidate request and exact reply correlation.
3. Materialize or reuse the exact rendered artifact without manual file repair.
4. Verify and migrate exactly one `v0.1.125` candidate.
5. Run focused live proof where needed and the mandatory full candidate profile with a suitable timeout.
6. Accept only through the passing candidate-test gate.
7. Prove `artifact current` and `candidate_mvp_complete`.
8. Carry this documentation and all updated draw.io pages into the release.

Out of scope:

- external application source mutation;
- application tests or application artifacts;
- deployment automation;
- broad autonomous shell authority.

Exit criterion:

```text
A second PB-environment lifecycle completes from accepted v0.1.124 to accepted v0.1.125 with no manual state or candidate-file repair between the canonical lifecycle steps.
```

### v0.1.126 — Persistent whole-release ETA estimator

Preserved scope:

- persist duration evidence per test profile, phase, transport, and step;
- estimate remaining duration and expected finish time;
- distinguish confidence and evidence source;
- expose timeout-risk diagnostics before an outer wrapper kills a healthy full run;
- provide profile-aware timeout recommendations without weakening fail-closed test results.

This is still PB environment work, not application development.

### v0.1.127 — Portable Promptbranch tool-authoring skill and export bundle

Preserved scope:

- package a portable `promptbranch-tool-authoring` skill;
- describe deterministic tool schemas, validation, authority, evidence, and failure semantics;
- export the skill for ChatGPT Project Sources and coding-agent use;
- keep tool authoring separate from granting unrestricted execution authority.

This extends PB as a control plane. It still does not constitute an external application-development proof.

## Extended roadmap

### v0.1.128 — PB environment MVP hardening and freeze

Goal: close the environment defects and policy ambiguities discovered during `v0.1.124`.

In scope:

- profile-sensitive candidate-test timeout defaults;
- automatic recovery of an exact registered candidate ZIP from its verified artifact inbox, or preservation across clean installs;
- post-execution recomputation of candidate-run top-level summaries;
- one documented mandatory-versus-optional test policy;
- explicit Project Source publication policy for PB releases;
- one canonical PB environment proof command sequence;
- clean-install proof with no manual registry or file repair.

Exit criterion:

```text
The PB environment can be installed fresh and can complete its documented mandatory lifecycle without manual candidate restoration, timeout override discovery, or interpretation of contradictory summary fields.
```

### v0.1.129 — External application pilot bootstrap

Goal: create **System B** without modifying it yet.

In scope:

- choose one small external application pilot in a separate repository;
- register project/repository identity and baseline;
- define product target, non-goals, architecture, risks, and Definition of Done;
- define one vertical slice and its application-specific tests;
- generate a read-only execution plan and execution envelope proposal;
- keep PB environment tests and app tests explicitly separate.

Exit criterion: PB can read and plan the external app with no source mutation and can show the exact app-specific evidence required for the first change.

### v0.1.130 — Controlled external application change execution

Goal: perform one human-authorized application change.

In scope:

- exact repository/path/tool allowlists;
- pre-change snapshot and rollback plan;
- execution-envelope validation;
- bounded source/config edits for one vertical slice;
- immutable evidence of inputs, changed files, commands, and outputs;
- no automatic candidate acceptance or deployment.

Exit criterion: one authorized application change is applied and can be deterministically rolled back.

### v0.1.131 — Application test, diagnosis, and bounded correction loop

Goal: prove the central PB problem-solving loop against application behavior.

In scope:

- run application unit/integration/acceptance tests;
- classify results as passed, blocked, or failed;
- identify the smallest evidence-supported correction;
- require authority before correction mutation;
- limit correction attempts and stop safely;
- retest and retain the full evidence chain.

Exit criterion: the pilot slice reaches green or a precise blocked verdict without uncontrolled mutation.

### v0.1.132 — External application candidate and acceptance lifecycle

Goal: complete the first application-development MVP.

In scope:

- build the application artifact;
- verify application version, integrity, layout, and hygiene;
- migrate it into an application-scoped candidate registry;
- run application release tests;
- explicitly accept it as the application's current baseline;
- prove that PB's own accepted artifact remains independent.

Exit criterion:

```text
PB drives one separate application from target and architecture through controlled source changes, application tests, a verified candidate artifact, and explicit application acceptance.
```

### v0.1.133 — Non-production deployment and post-deployment proof

Goal: extend the pilot to one explicit non-production deployment.

In scope:

- deployment adapter with exact environment authority;
- operator confirmation before deployment;
- pre-deployment state and rollback evidence;
- health/functional verification after deployment;
- explicit success, rollback, or blocked outcome;
- production deployment remains out of scope by default.

### v0.1.134 — Reusable PB application workflow and multi-repository generalization

Goal: generalize the proven pilot without weakening authority.

In scope:

- reusable application bootstrap templates;
- domain-module integration;
- app-specific test-profile templates;
- multi-repository dependency and release-set planning;
- reusable application candidate/publication flows;
- explicit deployment and recovery adapters;
- architecture and evidence migration rules.

## Release-line boundary

```text
v0.1.124          accepted PB artifact/candidate lifecycle checkpoint
v0.1.125–v0.1.128 PB environment/control-plane completion and hardening
v0.1.129–v0.1.132 first external application-development MVP
v0.1.133          non-production deployment proof
v0.1.134          reusable application-development platform
```

## Planning rule

Repairs may correct defects within the active slice but may not silently advance from PB environment work into application development. The transition to `v0.1.129` requires an explicit architecture decision that names the pilot repository, mutation authority, rollback contract, and application-specific test evidence.
