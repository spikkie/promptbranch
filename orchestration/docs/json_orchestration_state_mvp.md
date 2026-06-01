# JSON Orchestration State MVP — Architecture

## Purpose

The JSON Orchestration State MVP adds a typed planning/state layer above the finalized Final Artifact Intake MVP.

The new layer handles decisions, gates, state transitions, and evidence before release artifacts exist.

## One-line architecture

```text
ChatGPT reasons; JSON carries intent; Promptbranch validates state transitions; tools produce evidence; Artifact Intake accepts only verified releases.
```

## Why this exists

Local Ollama planning is not reliable enough for structured orchestration. Fully deterministic planning logic is safer but becomes brittle when workflow routing grows.

The replacement is:

```text
ChatGPT proposes structured planning events.
Promptbranch validates schemas and state transitions.
Promptbranch records accepted events as workflow state.
Promptbranch only allows controlled next actions.
```

## Layered architecture

```text
User
  ↓
Promptbranch Orchestration Context Builder
  ↓ JSON context
ChatGPT
  ↓ JSON proposal / decision / plan / artifact reply
Promptbranch Protocol Validator
  ↓
Orchestration State Machine
  ├─ records accepted planning events
  ├─ rejects invalid transitions
  ├─ requires gates and evidence
  └─ decides allowed next command
        ↓
      Execution and evidence layer
        ├─ tests
        ├─ build/package
        ├─ artifact intake/finalizer
        └─ deploy/smoke evidence
```

## Non-goals for v0.1.0

```text
- no generic orchestration engine
- no game implementation
- no deployment workflow
- no write-capable agent
- no automatic source/project mutation
- no automatic artifact release
- no local LLM planner
```

## Minimal proof for v0.1.0

v0.1.0 proves only that the repository has a small, typed, testable orchestration control surface.

Required proof surfaces:

```text
- context schema/example
- decision schema/example
- evidence schema/example
- one k8s-game-mvp state machine
- one k8s-game-mvp contract
- proposal-vs-accepted-event trust-boundary document
- branch strategy document
```
