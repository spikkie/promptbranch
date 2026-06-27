# JSON Orchestration State MVP — Current Status after v0.1.85

Updated for release: v0.1.86 planning reconciliation

## Purpose

This document reconciles the Kubernetes game orchestration plan with the accepted Promptbranch release line through `v0.1.85`.

The project remains on the same strategic goal:

```text
ChatGPT proposes structured JSON.
Promptbranch validates schema, policy, and state.
Only accepted events become trusted workflow state.
Artifacts still go through guarded artifact intake and adoption.
Kubernetes deployment requires explicit Promptbranch-controlled evidence gates.
```

## Current state

```text
latest accepted baseline:          chatgpt_claudecode_workflow-2_v0.1.85.zip
current reconciliation release:    v0.1.86
orchestration goal:                still active
k8s-game role:                     controlled test vehicle, not the product
execution authority:               Promptbranch only
critical-path provider:            ChatGPT only
local/Ollama provider:             rejected until new ADR + tests
Kubernetes mutation authority:     not opened by v0.1.86
```

## What has been completed

```text
v0.1.0  Opened the JSON Orchestration State MVP line.
v0.1.1-v0.1.39  Hardened shell workflow, browser profile isolation, task/message handling, artifact/source handling, and rate-limit diagnostics.
v0.1.40  Reconciled early detours and added the read-only grill schema foundation.
v0.1.41-v0.1.53  Hardened backend diagnostics, source mutation locks, VERSION-driven service metadata, and release adoption verification.
v0.1.54  Consolidated orchestration design/control surfaces under docs/design/orchestration.
v0.1.55  Connected read-only grill validation to the k8s-game MVP state-machine transition rules.
v0.1.56-v0.1.57  Added read-only accepted-event fixtures and validator coverage for G0-G6.
v0.1.58-v0.1.66  Added PB application design docs, docs-status guards, MkDocs source scaffold, release config guard, and release-doctor candidate prechecks.
v0.1.67-v0.1.78.2.20.8.8  Hardened project control surface, artifact adoption/current consistency, Project Source transaction diagnostics, live retained-project tests, and immutable Project deletion freeze.
v0.1.79  Resumed the normal JSON orchestration MVP line with proposal-only event-intake schema, read-only validator, CLI command, and fail-closed tests.
v0.1.80-v0.1.84  Added accepted-event validation, dry-run promotion preview, explicit input validation, ledger-status, and ledger validation while preserving no-write/no-deploy boundaries.
v0.1.84.1-v0.1.84.5.12.2  Repaired live validation, rate-limit, retained Project, source-add, ask-live, and explicit `pb ask --new-task` operator boundaries.
v0.1.85  Added schema-v2 ask state observability and canonical new-task proof hardening.
```

## Drift assessment

The plan is still strategically on track. The Kubernetes game remains the deliberately small vehicle used to prove the orchestration lifecycle, not a standalone product goal.

The current gap is documentation authority, not implementation capability:

```text
The accepted baseline advanced to v0.1.85.
Several orchestration docs still described the line as if v0.1.79 or older candidates were current.
The next game work must therefore start with plan reconciliation before any app or cluster files are added.
```

## Active safety boundary

The orchestration layer remains proposal-only:

```text
- no source mutation from ChatGPT proposals
- no artifact adoption from ChatGPT proposals
- no Kubernetes deployment from ChatGPT proposals
- no accepted-event ledger write outside explicit Promptbranch CLI authority
- no local/Ollama critical-path provider
- no model execution authority
```

Promptbranch may validate schemas, fixtures, accepted-event examples, and future dry-run previews. It must not deploy the k8s-game to a cluster until a later release adds an explicit Kubernetes deploy evidence gate.

## Reconciled next orchestration path

```text
v0.1.86
  K8s-game orchestration plan reconciliation:
  - update docs/project control surface to v0.1.85 baseline reality
  - refresh orchestration status, global plan, detailed handoff, and k8s-game contract
  - state that no game implementation or cluster mutation is performed in this slice

v0.1.87 candidate direction
  K8s-game static app artifact scaffold:
  - static HTML/CSS/JS files only
  - Dockerfile and Kubernetes manifest files as repository artifacts only
  - local/static validation and manifest linting only
  - no kubectl apply, no Helm install, no cluster mutation

v0.1.88 candidate direction
  K8s-game Kubernetes dry-run/deploy evidence gate:
  - add explicit dry-run validation and operator-controlled deploy evidence contract
  - actual cluster mutation remains blocked until the gate is explicit and accepted
```

## Do not start yet

Do not implement or deploy the game in `v0.1.86`. This slice only reconciles planning authority and release baseline continuity.

## v0.1.87 current status — loop target schema and dry-run planner

Current accepted baseline: `chatgpt_claudecode_workflow-2_v0.1.86.zip`.

Current candidate direction: `v0.1.87 — Loop target schema and dry-run planner`.

The candidate is side-effect free. It validates target definitions and emits dry-run loop plans only. K8s-game work is represented as a future target fixture, not as implementation or deployment.


## v0.1.92 current status — MVP-1 state-only loop walkthrough

After the accepted/current `v0.1.91.10` release-control foundation proof, MVP-1 opens with a state-only loop walkthrough. The command `pb loop run --target examples/loop-targets/static-game-dry-run-target.json --state-only` prints only the planned state sequence and remains side-effect free.

This slice does not implement the Kubernetes game, execute validation commands, mutate files, deploy to Kubernetes, mutate Project Sources, or adopt artifacts. The Kubernetes game remains the first future acceptance scenario for the loop once state walkthrough and later controlled action gates are proven.


## v0.1.93 planned-action walkthrough

MVP-1 advances from state-only output to a planned-action walkthrough. `pb loop run --planned-actions` prints the planned action and validation gate for each loop state while remaining fully side-effect free. This prepares the future execution loop without granting execution authority yet.


## v0.1.94 update

MVP-1 now includes a read-only execution preflight: `pb loop run --read-only-checks`. The command inspects target-declared path scopes and validation command declarations locally while preserving all no-command/no-mutation/no-deployment/no-adoption guarantees.
