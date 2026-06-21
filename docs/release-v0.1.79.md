# Release v0.1.79 — JSON orchestration event intake foundation

## Baseline

```text
chatgpt_claudecode_workflow-2_v0.1.78.2.20.8.8.zip
```

## Type

```text
normal MVP release
```

## Scope

`v0.1.79` resumes the JSON orchestration MVP line after the `.8.x` repair chain. It adds a narrow proposal-only event-intake surface.

## Added

- `docs/design/orchestration/schemas/event_intake.schema.json`
- `docs/design/orchestration/examples/events/v0.1.79_event_intake.example.json`
- `promptbranch_orchestration.py`
- `scripts/orchestration/validate_event_intake.py`
- `pb orchestration validate-event`
- `tests/orchestration/test_event_intake_foundation.py`
- `docs/design/orchestration/docs/event_intake_foundation.md`

## Safety invariants

A valid event-intake proposal does not mean accepted workflow state. It only means the proposal passed read-only validation and may be reviewed.

The validator rejects proposals that allow runtime state mutation, Project Source mutation, artifact adoption, deployment, or model execution.

## Validation planned

Focused local validation must include event-intake tests, orchestration fixture tests, project control-surface tests, version tests, compileall, bash syntax, and ZIP hygiene. Full release-control and adoption/current verification remain operator-side gates.


## Candidate correction — default event examples

The no-argument CLI path must validate committed default event-intake examples from the repository working tree when available. It must not return `ok=true` with `validated_count=0` for the default command. If no default examples are discoverable, the validator fails closed with a diagnostic and keeps all proposal-only/no-mutation invariants false.

Expected operator smoke:

```bash
pb orchestration validate-event --json
```

Expected signal: `ok=true`, `validated_count >= 1`, and no accepted state, Project Source, artifact adoption, deployment, or model-execution mutation.
