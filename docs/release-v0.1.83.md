# Release candidate v0.1.83 — Accepted-event ledger design scaffold

## Status

```text
candidate only
focused working slice
not accepted/current
```

Accepted/current remains `chatgpt_claudecode_workflow-2_v0.1.79.zip` until later full validation and adoption evidence proves otherwise.

## Scope

`v0.1.83` adds a read-only accepted-event ledger scaffold.

New command:

```bash
pb orchestration ledger-status --json
```

The command reports the future append-only ledger path, record schema path, record count when a ledger exists, and the current no-write/no-mutation authority boundary.

## Out of scope

- `accept-event --write`.
- Accepted-event ledger creation.
- Accepted-event ledger append.
- Project Source mutation.
- Artifact adoption/current mutation.
- Deployment or model execution.

## Validation

Focused local validation for this candidate:

```bash
python3 promptbranch_cli.py orchestration ledger-status --json
python3 promptbranch_cli.py orchestration accept-event --dry-run --json docs/design/orchestration/examples/accepted_events/G0_intent.accepted_event.example.json
python3 -m pytest -q tests/orchestration/test_orchestration_accepted_event_schema.py tests/orchestration/test_event_intake_foundation.py tests/test_cli_parser.py tests/test_promptbranch_version.py tests/test_project_control_surface.py
python3 -m compileall -q .
bash -n chatgpt_claudecode_workflow_release_control.sh
pb artifact guard --zip chatgpt_claudecode_workflow-2_v0.1.83.zip --json
```

Full all-tests and adoption/current are intentionally deferred for the focused-slice workflow.
