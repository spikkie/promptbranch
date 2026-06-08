# JSON Orchestration State MVP — Global MVP Plan

## Purpose

This global plan defines the v0.1.x MVP line for JSON Orchestration State.

The plan starts from:

```text
chatgpt_claudecode_workflow_v0.0.278.86.zip
```

and opens the new branch:

```text
mvp/json-orchestration-state-v0.1.0
```

## Strategic goal

Promptbranch should move from artifact intake alone to typed orchestration state.

The goal is not autonomous execution. The goal is controlled planning state:

```text
ChatGPT proposes structured JSON.
Promptbranch validates schema/policy/state.
Only accepted events become trusted workflow state.
Artifacts still go through Final Artifact Intake.
```

## MVP line

```text
v0.1.0
  Documentation/planning foundation:
  - global/detailed plans
  - high/low canvases
  - context/decision/evidence schemas
  - examples
  - k8s-game state machine
  - ChatGPT-only provider decision

v0.1.1
  promptbranch.orchestration.grill:
  - grill schema
  - G0-G6 examples
  - read-only validation
  - provider.kind=chatgpt policy
  - provider.kind=ollama rejected

v0.1.2
  K8s-game grill fixture set:
  - G0-G3 project-specific grilling examples
  - transition checks
  - next-stage recommendation fixtures

v0.1.3
  First implementation candidate planning:
  - use grilling loop before game implementation
  - still no deployment until release/deployment evidence model is ready

v0.1.4
  Deployment evidence loop:
  - capture rollout/smoke evidence as validated evidence JSON
```


## Current release-line reconciliation

The original `v0.1.1`-`v0.1.4` sequence remains the intended orchestration direction, but the actual line first absorbed control-plane hardening through `v0.1.39`.

This was acceptable because those releases protected baseline continuity, browser/profile isolation, task/message handling, artifact/source handling, and rate-limit safety. It did create documentation drift, so `v0.1.40` explicitly reconciles the state and resumes the read-only grill slice.

Reconciled path:

```text
v0.1.40
  Documentation/status reconciliation plus promptbranch.orchestration.grill foundation:
  - grill schema
  - G0-G6 examples
  - read-only validation
  - provider.kind=chatgpt or manual_fixture only
  - provider.kind=ollama/local_llm rejected
  - model_may_execute=true rejected
  - promptbranch_must_validate=false rejected

next narrow orchestration slice
  Read-only grill-to-state-machine transition validation.
```

## Global non-goals

```text
- ChatGPT as execution authority
- Ollama/local LLM as critical-path provider
- automatic artifact adoption from model output
- source mutation from grill output
- Kubernetes deployment before release evidence gates exist
- generic workflow engine before one test vehicle proves the model
```

## Global test vehicle

```text
project: k8s-game-mvp
purpose: controlled lifecycle test vehicle
not: game product
```

The game exists to test:

```text
idea -> grill -> architecture -> slice -> code -> test -> package -> deploy -> maintain
```

## Provider policy

v0.1.x critical-path provider:

```text
ChatGPT only
```

Reason:

```text
Local larger-model Ollama bakeoff failed the configured validation threshold.
```

Future local model support requires:

```text
1. passing bakeoff
2. new ADR
3. provider policy update
4. negative tests remain for unapproved providers
```

## Governance rule

Every LLM output remains untrusted until Promptbranch validates it.

```text
LLM proposal != accepted event
```
