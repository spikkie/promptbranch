# Repair Release v0.1.18.1

## Base release

`v0.1.18`

## Repair version

`v0.1.18.1`

## Reason

The `v0.1.18` full release-control retry repeated a cleanup-only browser-suite failure:

```text
project_remove_cleanup_failed
504 error for POST http://localhost:8000/v1/projects/remove: Could not find the configured project in the sidebar
```

All functional browser steps, the agent suite, version consistency, and rate-limit checks were otherwise green. The failing cleanup postcondition was already satisfied: the temporary project was absent. Treating that condition as a hard release failure made cleanup non-idempotent.

## Files changed

- `promptbranch_full_integration_test.py`
- `tests/test_full_integration_harness.py`
- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `docker-compose.chatgpt-service.yml`
- `docs/release-v0.1.18.1.md`

## Repair behavior

`project_remove_cleanup` now treats a final "configured project not found in sidebar" cleanup result as idempotent success with structured status:

```text
project_remove_cleanup_already_missing
```

This applies only to the cleanup step. It does not weaken project creation, source operations, ask/task validation, or agent tests.

## Validation performed

Focused validation was performed against the repair surface and release/version packaging checks. Full browser/service/adoption validation remains the operator checkpoint for accepting the repair.

## Slice / line advancement

No slice or line was advanced. This repair fixes only the repeated `v0.1.18` validation failure.
