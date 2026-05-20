# Repair v0.0.245.2

Base release: v0.0.245.1
Repair version: v0.0.245.2

## Reason

`v0.0.245.1` still failed the final Artifact Intake MVP protocol-smoke gate for valid `no_artifact` / `no_change` replies. The validator checked `parsed["status"]`, which is the parser status (`valid`), instead of the actual reply-envelope status exposed as `parsed["reply_status"]` or `parsed["reply"]["status"]`.

## Files changed

- `promptbranch_cli.py`
- `tests/test_promptbranch_cli.py`
- version metadata surfaces

## Validation performed

- Python compile checks
- focused protocol-validator regression tests
- focused release doctor / MVP status / version tests
- shell syntax checks for release scripts
- ZIP CRC and hygiene checks

## Scope confirmation

No normal release slice was advanced. This repair only fixes the intended `v0.0.245` validator behavior.
