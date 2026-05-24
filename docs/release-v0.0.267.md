# Release v0.0.267

## Scope

Read-only lifecycle-status consolidation release from `chatgpt_claudecode_workflow_v0.0.266.zip`.

## Added

- `pb release lifecycle-status --json`
- Local-first lifecycle status payload for runtime, VERSION file, installed distribution, artifact current state, candidate inventory, candidate-next, latest post-release validation summary, lifecycle phase, Git status, consistency warnings/blockers, and next safe action.
- Optional probes:
  - `--include-service-health`
  - `--include-project-sources`

## Safety boundary

The command is read-only. By default it skips service health and Project Sources to avoid browser/session/service dependencies during local status inspection.

No artifact download, candidate migration, candidate testing, adoption, Project Source mutation, artifact registry update, Promptbranch state update, Git commit, or Git push is performed.

## Validation

- `python3 -m py_compile promptbranch_cli.py tests/test_promptbranch_cli.py tests/test_cli_parser.py`
- Focused parser and lifecycle-status tests.
- Focused finalizer-classification tests.
- ZIP CRC/layout/hygiene verification after packaging.
