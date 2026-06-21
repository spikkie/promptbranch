# Event Intake Foundation — v0.1.79

## Purpose

`v0.1.79` adds the first small JSON orchestration intake surface for the resumed MVP line.

The invariant is strict:

```text
ChatGPT proposal JSON is not workflow authority.
Promptbranch validates the proposal.
A valid proposal is still not accepted state.
```

## Schema

The committed schema is:

```text
docs/design/orchestration/schemas/event_intake.schema.json
```

Schema identity:

```text
promptbranch.orchestration.event_intake
```

## Validator

The validator is available through both paths:

```bash
scripts/orchestration/validate_event_intake.py --json
pb orchestration validate-event --json
```

Both paths are read-only. They do not write accepted state, mutate Project Sources, adopt artifacts, deploy, or execute model-proposed actions.

## Default fixture

The committed example is:

```text
docs/design/orchestration/examples/events/v0.1.79_event_intake.example.json
```

## Fail-closed rules

Validation fails when proposal JSON attempts to allow:

```text
runtime_state_mutation_allowed=true
source_mutation_allowed=true
artifact_adoption_allowed=true
deployment_allowed=true
model_may_execute=true
```

Validation also rejects absolute paths and parent-relative paths in repo/path surfaces.

## Out of scope

- k8s-game runtime implementation.
- Generic orchestration engine.
- Accepted-event ledger writes.
- Artifact adoption.
- Project Source mutation.
- ChatGPT Project deletion.
