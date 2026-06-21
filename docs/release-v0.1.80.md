# Release v0.1.80

## Name

Accepted-event validation foundation

## Baseline

```text
chatgpt_claudecode_workflow-2_v0.1.79.zip
```

## Scope

`v0.1.80` adds a read-only accepted-event validation foundation after the `v0.1.79` JSON event-intake layer.

Implemented:

- `pb orchestration validate-accepted-event --json`;
- no-arg validation of committed G0-G6 accepted-event fixtures;
- explicit-path accepted-event validation;
- accepted-event fixture baseline binding to the accepted/current `v0.1.79` artifact/source;
- fail-closed zero-default behavior;
- tests for mutation boundaries, baseline binding, stale hashes, bad transitions, and unsafe paths.

## Non-mutating guarantees

The accepted-event validator is read-only:

```text
fixture_only=true
accepted_state_written=false
runtime_state_mutation_allowed=false
source_mutation_allowed=false
artifact_adoption_allowed=false
deployment_allowed=false
model_may_execute=false
```

## Out of scope

- Accepted-event ledger write path.
- Proposal promotion / accept-event write.
- Runtime orchestration engine.
- k8s-game implementation or deployment.
- Project Source behavior changes.
- Artifact adoption/current behavior changes beyond normal release-control adoption.

## Validation performed before ZIP handoff

Focused local validation only:

- accepted-event validator CLI smoke;
- event-intake validator CLI smoke;
- orchestration accepted-event tests;
- orchestration event-intake/grill/example tests;
- project-control and version tests;
- compileall;
- release-control shell syntax;
- artifact guard / ZIP hygiene.

Full release-control, Project Source add, Docker service, live headed tests, and artifact adoption/current verification remain operator-side validation steps.
