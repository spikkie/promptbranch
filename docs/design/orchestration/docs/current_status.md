# JSON Orchestration State MVP — Current Status after v0.1.56

Updated for release: v0.1.56

## Purpose

This document reconciles the original `v0.1.x` orchestration objective with the actual accepted release line through accepted repair `v0.1.55.1` and the v0.1.56 read-only accepted-event fixture validation slice.

The project remains on the same strategic goal:

```text
ChatGPT proposes structured JSON.
Promptbranch validates schema, policy, and state.
Only accepted events become trusted workflow state.
Artifacts still go through Final Artifact Intake.
```

## Current state

```text
latest accepted baseline:          v0.1.55.1
current development release:       v0.1.56
orchestration goal:                still active
execution authority:               Promptbranch only
critical-path provider:            ChatGPT only
local/Ollama provider:             rejected until new ADR + tests
```

## What has been completed

```text
v0.1.0  Opened the JSON Orchestration State MVP line.
v0.1.1  Continued orchestration foundation and validation work.
v0.1.20-v0.1.37  Hardened release-control, task/message, source/artifact, and validation surfaces needed by the shell workflow.
v0.1.38  Added browser profile lease/pool support so live tests do not collide on the same profile.
v0.1.39  Added read-only rate-limit diagnostics and backend API surface documentation.
v0.1.40  Reconciled these detours and added the read-only grill schema foundation.
v0.1.41-v0.1.53  Hardened backend diagnostics, source mutation locks, VERSION-driven service metadata, and release adoption verification.
v0.1.54  Consolidated the orchestration design/control surfaces under docs/design/orchestration and refreshed the living MVP design references.
v0.1.54.1  Repaired Project Source file persistence verification so file-source matches must be filename-anchored.
v0.1.55  Connects read-only grill validation to the k8s-game MVP state-machine transition rules.
v0.1.55.1  Repairs grill validator CLI path-label handling without advancing MVP scope.
v0.1.56  Adds a read-only accepted-event fixture and validator that consumes a valid grill recommendation without mutating runtime state.
```

## Drift assessment

The releases after the original `v0.1.0` plan are not goal drift by themselves. They are operational hardening needed to make the control plane safer.

The remaining risk is not conceptual drift, but authority drift:

```text
A ChatGPT grill envelope can recommend a next state.
Promptbranch must verify that the recommendation is allowed by the state machine.
The recommendation must remain proposal-only until a later accepted-event path records it.
```

v0.1.55 reduced that risk by validating each committed G0-G6 grill fixture against the canonical k8s-game MVP state machine. Invalid transitions, stage/transition mismatches, and project/state-machine mismatches now fail the read-only grill validator.

v0.1.56 adds the next boundary: a committed accepted-event fixture must reference a valid grill fixture, preserve the source grill SHA-256, match the source recommendation, and match the canonical k8s-game MVP state machine. The fixture remains data-only and cannot record live workflow state.

## Active safety boundary

The grill layer is still proposal-only:

```text
- no source mutation
- no artifact adoption
- no Kubernetes deployment
- no local/Ollama critical-path provider
- no model execution authority
```

Promptbranch may validate grill envelopes and accepted-event fixtures. In v0.1.56 the accepted event remains a committed read-only fixture only; it does not update Promptbranch runtime state or artifact/source registries.

## Next planned orchestration work

After this release is accepted, the next narrow slice should remain read-only and may be selected from the consolidated living design:

```text
- add more accepted-event fixtures for G1-G6 so every grill stage has a read-only accepted-event counterpart
- add rejected-event fixtures that prove invalid grill recommendations remain non-authoritative
- extend docs-status so it checks accepted-event fixture coverage and source-grill hash freshness
```

Do not start game implementation or write-capable orchestration until the design/control surfaces remain stable after the state-machine transition validation slice.
