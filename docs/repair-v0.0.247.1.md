# Repair v0.0.247.1

## Base release

`chatgpt_claudecode_workflow_v0.0.247.zip`

## Repair version

`v0.0.247.1`

## Reason

The `v0.0.247` final Artifact Intake MVP validation failed in the live Project Source overwrite path. A same-file source upload could persist successfully but still be classified as a fresh add when the next request started from a stale or empty Sources snapshot.

## Files changed

- `promptbranch_automation/service.py`
- `tests/test_promptbranch_automation_service.py`
- version metadata surfaces (`VERSION`, `pyproject.toml`, `promptbranch_version.py`, container/version tests, MCP/version tests)

## Repair behavior

The automation service now remembers a verified file Project Source after `persistence_verified=true`. On the next same-file add with overwrite enabled, it treats the remembered verified source as authoritative before-state, removes it before upload, and classifies the successful second upload as an overwrite only after the new upload is also persistence-verified.

If the remembered-source remove cannot be verified, the service fails closed with `remembered_overwrite_remove_failed` or `remembered_overwrite_remove_not_verified`, clears the remembered identity, and does not fabricate overwrite success.

## Validation performed

- `py_compile` for changed runtime/test files.
- Focused service tests for remembered overwrite classification and fail-closed remove handling.
- Broader focused regression tests before packaging.
- ZIP CRC/layout/hygiene verification after packaging.

## Scope confirmation

No slice or line was advanced. This repair does not change protocol schema, artifact intake core semantics, candidate lifecycle semantics, adoption semantics, or release config parser scope.
