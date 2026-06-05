# JSON Orchestration State MVP

This directory contains the v0.1.x JSON Orchestration State MVP foundation and the reconciled read-only grill validation surface.

The purpose is to define a small, typed, repo-relative control surface for orchestration decisions before release artifacts exist.

The key split is strict:

```text
ChatGPT proposal          = untrusted model output
Promptbranch accepted event = trusted workflow state after validation
Tool evidence            = deterministic output from tests/deploy/release checks
Release artifact         = handled by the Final Artifact Intake MVP
```

Version line:

```text
v0.0.278.86 = fixed Final Artifact Intake MVP baseline
v0.1.x     = JSON Orchestration State MVP line
```

v0.1.0 was intentionally documentation/data-surface first. v0.1.40 reconciles the actual release line through v0.1.39 and adds a read-only grill schema/validator. It still does not implement a generic orchestration engine, Kubernetes game code, deployment automation, or write-capable agent execution.

## Contents

```text
orchestration/docs/            Human-readable architecture and operating docs
orchestration/schemas/         JSON schema contracts for context, decision, evidence, grill
orchestration/examples/        Small fixture examples for future validation, including G0-G6 grill examples
orchestration/state_machines/  First project-specific state machine, k8s-game-mvp
```

## Design rule

```text
ChatGPT reasons.
Promptbranch validates.
State machine orchestrates.
Tools produce evidence.
Artifact Intake adopts only verified release artifacts.
```
