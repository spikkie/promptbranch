# JSON Orchestration State MVP — Current Status after v0.1.39

Updated for release: v0.1.40

## Purpose

This document reconciles the original `v0.1.x` orchestration objective with the actual release line through `v0.1.39`.

The project remains on the same strategic goal:

```text
ChatGPT proposes structured JSON.
Promptbranch validates schema, policy, and state.
Only accepted events become trusted workflow state.
Artifacts still go through Final Artifact Intake.
```

## Current state

```text
latest reconciled input release: v0.1.39
current reconciliation release:   v0.1.40
orchestration goal:              still active
execution authority:             Promptbranch only
critical-path provider:          ChatGPT only
local/Ollama provider:           rejected until new ADR + tests
```

## What has been completed

```text
v0.1.0  Opened the JSON Orchestration State MVP line.
v0.1.1  Continued orchestration foundation and validation work.
v0.1.20-v0.1.37  Hardened release-control, task/message, source/artifact, and validation surfaces needed by the shell workflow.
v0.1.38  Added browser profile lease/pool support so live tests do not collide on the same profile.
v0.1.39  Added read-only rate-limit diagnostics and backend API surface documentation.
v0.1.40  Reconciles these detours and adds the read-only grill schema foundation.
```

## Drift assessment

The releases after the original `v0.1.0` plan are not goal drift by themselves. They are operational hardening needed to make the control plane safer.

The drift was documentation drift:

```text
The original orchestration docs still described the planned v0.1.1-v0.1.4 path as if it were the active release sequence.
The actual line spent many releases hardening release-control, profile isolation, task/message handling, and rate-limit behavior.
```

This release corrects that by documenting the detour and resuming the next orchestration slice: read-only grill envelopes.

## Active safety boundary

The grill layer is still proposal-only:

```text
- no source mutation
- no artifact adoption
- no Kubernetes deployment
- no local/Ollama critical-path provider
- no model execution authority
```

Promptbranch may validate grill envelopes. It must not treat a grill output as an accepted event until a later accepted-event path explicitly validates and records it.

## Next planned orchestration work

After this release is accepted, the next narrow slice should connect grill validation to the k8s-game MVP state machine without introducing mutation:

```text
- map G0-G6 grill stages to allowed state-machine transitions
- keep output read-only
- reject invalid transition recommendations
- preserve provider.kind policy
- preserve model_may_execute=false
```
