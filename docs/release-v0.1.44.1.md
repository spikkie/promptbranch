# Release v0.1.44.1 Repair Note

Base release: v0.1.44
Repair version: v0.1.44.1

## Reason

The v0.1.44 lightweight live-smoke command documented `pb src add ... --json`, but the `src add` and legacy `project-source-add` parsers did not accept `--json` at the subcommand level. The command itself remained JSON-first, but automation failed before execution with `unrecognized arguments: --json`.

## Files changed

- `promptbranch_cli.py`
- `promptbranch_version.py`
- `pyproject.toml`
- `VERSION`
- `README.md`
- `UPGRADING.md`
- `docker-compose.chatgpt-service.yml`
- `tests/test_cli_parser.py`
- `tests/test_promptbranch_cli.py`
- `docs/release-v0.1.44.1.md`

## Validation performed

- `python3 -m compileall -q .`
- focused parser/CLI regression tests for `src add --json` and `project-source-add --json`
- cumulative lightweight Promptbranch parallel/profile/scheduler tests
- strict JSON command smokes
- artifact-roundtrip smoke
- ZIP hygiene verification

## Scope confirmation

No normal slice, scheduler line, source mutation semantics, or service profile execution model was advanced. This repair only aligns parser support with the advertised v0.1.44 command contract.
