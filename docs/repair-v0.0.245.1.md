# Repair v0.0.245.1

## Base release

`chatgpt_claudecode_workflow_v0.0.245.zip`

## Repair version

`v0.0.245.1`

## Reason

`v0.0.245` installed and ran successfully, but the final Artifact Intake MVP/post-release validation failed during protocol smoke. The protocol reply was a valid `no_artifact` / `no_change` envelope for target `v0.0.246`, but reply validation reported `target_version_mismatch` because it required `baseline.output_version` to match the requested target even when no artifact was produced.

## Files changed

- `promptbranch_cli.py`
- `tests/test_promptbranch_cli.py`
- version metadata surfaces for `v0.0.245.1`
- this repair note

## Validation performed

- `python3 -m py_compile` on changed Python modules
- focused protocol reply validation regression tests
- focused parser/version/container/MCP smoke tests
- ZIP CRC and hygiene checks

## Scope confirmation

No normal release scope, slice state, artifact intake workflow, adoption behavior, Docker behavior, or Project Source mutation behavior was advanced. This repair only fixes the validator rule for no-artifact protocol smoke replies and updates version metadata to the canonical repair version.
