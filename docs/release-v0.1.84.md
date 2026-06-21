# Release v0.1.84 — Accepted-event ledger validation command

## Status

Focused working candidate only. This ZIP is not accepted/current.

Accepted/current baseline remains:

```text
chatgpt_claudecode_workflow-2_v0.1.79.zip
```

Working candidate context:

```text
v0.1.83 focused-validated candidate
```

## Scope

This slice adds a read-only ledger validation command:

```bash
pb orchestration validate-ledger --json
```

The command validates the accepted-event ledger contract without creating the ledger, appending records, writing accepted state, mutating ChatGPT Project Sources, adopting artifacts, deploying, or executing model-proposed actions.

## Expected empty-ledger result

For the current pre-write MVP slice, an absent ledger is valid when the ledger directory and record schema scaffold are present:

```text
ok=true
status=accepted_event_ledger_absent_valid
ledger_exists=false
record_count=0
ledger_write_performed=false
write_command_available=false
accept_event_write_supported=false
```

## Out of scope

- `accept-event --write`
- ledger creation
- ledger append
- accepted-state mutation
- Project Source mutation
- artifact adoption/current mutation
- deployment
- model execution

## Validation

Focused local validation completed before ZIP packaging:

```bash
python3 promptbranch_cli.py orchestration validate-ledger --json
python3 -m pytest -q \
  tests/orchestration/test_orchestration_accepted_event_schema.py \
  tests/orchestration/test_event_intake_foundation.py \
  tests/test_cli_parser.py \
  tests/test_promptbranch_version.py \
  tests/test_project_control_surface.py
python3 -m compileall -q .
bash -n chatgpt_claudecode_workflow_release_control.sh
python3 artifact_guard.py . --json
```

Full all-tests, Project Source add, artifact adoption/current verification, and Git push were not run for this focused candidate.
