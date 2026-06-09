# Release v0.1.56 — Read-only accepted-event fixture validation

## Base release

```text
chatgpt_claudecode_workflow-2_v0.1.55.1.zip
```

## Purpose

This release continues the JSON Orchestration State MVP by adding the first
read-only accepted-event proof surface.  The accepted event consumes a valid
`promptbranch.orchestration.grill` recommendation and verifies that it matches
the canonical k8s-game MVP state machine without mutating runtime workflow state.

## Scope

Added:

```text
docs/design/orchestration/schemas/accepted_event.schema.json
docs/design/orchestration/examples/accepted_events/G0_intent.accepted_event.example.json
scripts/orchestration/validate_accepted_event.py
tests/orchestration/test_orchestration_accepted_event_schema.py
```

Updated:

```text
VERSION
pyproject.toml
promptbranch_version.py
docs/design/orchestration/docs/current_status.md
docs/design/promptbranch-mvp-living-design.md
docs/design/promptbranch-mvp-gap-analysis.md
```

## Design boundary

The accepted-event fixture is still data-only:

```text
runtime_state_mutation_allowed = false
source_mutation_allowed        = false
artifact_adoption_allowed      = false
deployment_allowed             = false
model_may_execute              = false
promptbranch_must_validate     = true
```

The validator performs deterministic local checks only. It does not call
ChatGPT, Ollama, browser sessions, Kubernetes, source-sync, artifact adoption,
or Promptbranch registry mutation paths.

## Validation behavior

`validate_accepted_event.py` verifies:

```text
- accepted-event schema identity and version
- project id matches the k8s-game MVP state machine
- source grill path is repo-relative and exists
- source grill SHA-256 matches the committed fixture
- source grill validates through validate_grill.py
- accepted transition is a legal k8s-game MVP state-machine transition
- accepted transition matches the source grill recommendation
- mutation/adoption/deployment/model-execution constraints are false
- evidence declares both grill and accepted-event validators
```

## Non-goals

This release does not add:

```text
- runtime workflow-state recording
- source mutation
- artifact adoption
- Kubernetes game implementation
- deployment automation
- Ollama/local LLM provider support
- write-capable orchestration engine
```

## Validation performed

```text
python3 scripts/orchestration/validate_examples.py
python3 scripts/orchestration/validate_grill.py
python3 scripts/orchestration/validate_accepted_event.py
python3 -m pytest -q tests/orchestration/test_orchestration_examples.py tests/orchestration/test_orchestration_grill_schema.py tests/orchestration/test_orchestration_accepted_event_schema.py
python3 promptbranch_cli.py release docs-status --version v0.1.56 --json
python3 -m compileall -q .
```
