# Release v0.1.82 — Accepted-event dry-run explicit input support

## Status

Candidate only. This slice is a focused working candidate built from the `v0.1.81` focused working candidate context. Accepted/current remains `chatgpt_claudecode_workflow-2_v0.1.79.zip` until a later full promotion/adoption gate verifies runtime, state artifact, state source, registry current, and consistency alignment.

## Baseline context

- Accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.79.zip`
- Working candidate context: `v0.1.80` -> `v0.1.81`
- Candidate artifact: `chatgpt_claudecode_workflow-2_v0.1.82.zip`

## Scope

`v0.1.82` makes explicit accepted-event input files a first-class dry-run contract:

```bash
pb orchestration accept-event --dry-run --json <accepted-event-file>
```

The command validates the supplied accepted-event file, returns a single-record preview when valid, and fails closed for missing, invalid, parent-relative, or repository-external paths.

## Invariants

- No accepted-event ledger write.
- No runtime state mutation.
- No Project Source mutation.
- No artifact adoption.
- No deployment.
- No model execution.
- Explicit input paths must resolve inside the repository root.
- Parent-relative paths are rejected.
- External absolute paths are rejected even if the file content is otherwise valid.

## Validation performed before handoff

- `python3 promptbranch_cli.py orchestration accept-event --dry-run --json docs/design/orchestration/examples/accepted_events/G0_intent.accepted_event.example.json`
- `python3 promptbranch_cli.py orchestration validate-accepted-event --json docs/design/orchestration/examples/accepted_events/G0_intent.accepted_event.example.json`
- Dedicated changed-code pytest group for accepted-event dry-run, event-intake, CLI parser, version, and project control surface.
- `python3 -m compileall -q .`
- `bash -n chatgpt_claudecode_workflow_release_control.sh`
- Artifact Guardian ZIP check.

## Not performed

- Installed pipx runtime validation by the operator.
- Docker service health.
- Project Source add.
- Broad release-control tests.
- Full all-tests.
- Artifact adoption/current verification.
- Git commit/push.
