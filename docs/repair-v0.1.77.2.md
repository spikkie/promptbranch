# Repair v0.1.77.2 — Temporary project cleanup retry and release-validation isolation

## Base release

```text
v0.1.77.1
```

## Repair version

```text
v0.1.77.2
```

## Reason

`v0.1.77.1` correctly stopped treating `project_remove` sidebar-not-found as success without absence verification, but the full release-control run exposed two remaining defects:

1. Cleanup failed closed after the first sidebar-not-found event even when the project was still resolvable by exact name and more cleanup attempts were available.
2. The required `browser_scheduler_source_lifecycle` release-validation group timed out without diagnostic output in the operator environment.

## Files changed

```text
promptbranch_full_integration_test.py
promptbranch_test_suite.py
tests/test_full_integration_harness.py
tests/test_promptbranch_test_suite.py
docs/repair-v0.1.77.2.md
docs/project/definition-of-done.md
docs/project/plan.md
docs/project/status.md
docs/project/release-status.md
docs/project/decisions.md
docs/project/migration.md
VERSION
pyproject.toml
promptbranch_version.py
tests/test_promptbranch_version.py
```

## Repair scope

In scope:

```text
- retry cleanup when sidebar-not-found is not absence-verified and attempts remain
- retarget cleanup to the exact URL returned by `resolve_project` when available
- verify absence after successful cleanup when the temporary project name is known
- disable ambient pytest plugin autoload for deterministic release-validation subprocesses
- add focused tests for cleanup retry/retarget behavior and validation subprocess environment
```

Out of scope:

```text
- repo-loop semantics
- registry/adoption semantics
- Project Source upload behavior
- release-set orchestration
- Docker/deployment behavior
- new normal release scope
```

## Validation performed

Focused validation was run before packaging:

```text
python3 -m pytest -q tests/test_full_integration_harness.py -k project_remove_cleanup
python3 -m pytest -q tests/test_promptbranch_test_suite.py -k release_validation_group
python3 -m pytest -q tests/test_promptbranch_version.py tests/test_project_control_surface.py
python3 -m pytest -q tests/test_promptbranch_automation_service.py tests/test_promptbranch_service_client.py tests/test_promptbranch_cli.py -k "scheduler or profile_busy or queue_wait or source_remove or cleanup or release_lifecycle_plan"
python3 -m compileall -q .
```

## Slice/line advancement

```text
No normal slice advanced.
No release line advanced.
This is a repair of the intended v0.1.77 release.
```
