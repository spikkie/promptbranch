# Accepted-event validation foundation

`v0.1.80` adds the accepted-event validation layer after the `v0.1.79` proposal/event-intake foundation.

## Purpose

Accepted events are trusted workflow-state candidates only after deterministic Promptbranch validation. In this slice they remain committed fixtures and read-only proof surfaces. The validator proves that an accepted-event fixture is structurally valid, baseline-bound, consistent with its source grill recommendation, and constrained against mutation/execution authority.

## Command

```bash
pb orchestration validate-accepted-event --json
```

With no explicit path, the command validates the committed G0-G6 accepted-event examples under:

```text
docs/design/orchestration/examples/accepted_events/
```

Operators may also pass explicit accepted-event JSON files:

```bash
pb orchestration validate-accepted-event docs/design/orchestration/examples/accepted_events/G0_intent.accepted_event.example.json --json
```

## Authority boundary

A valid accepted-event fixture still does not write trusted runtime state.

The command reports these invariants:

```text
fixture_only=true
accepted_state_written=false
runtime_state_mutation_allowed=false
source_mutation_allowed=false
artifact_adoption_allowed=false
deployment_allowed=false
model_may_execute=false
```

## Baseline binding

Each accepted-event fixture must bind to the accepted/current baseline that the fixture was validated against:

```text
baseline.artifact_ref
baseline.artifact_version
baseline.source_ref
baseline.source_version
baseline.role=accepted_current_source_baseline
```

For `v0.1.80`, the baseline is:

```text
chatgpt_claudecode_workflow-2_v0.1.79.zip
```

## Non-goals

This slice does not add:

- accepted-event ledger writes;
- proposal promotion;
- autonomous model execution;
- Project Source mutation;
- artifact adoption/current mutation;
- deployment or k8s-game runtime implementation.
