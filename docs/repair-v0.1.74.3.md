# Repair v0.1.74.3 — Full integration source-mutation wait alignment

Status: candidate repair  
Base accepted release: v0.1.73.4  
Failed normal release: v0.1.74  
Failed repair releases: v0.1.74.1, v0.1.74.2  
Repair version: v0.1.74.3

## Reason

`v0.1.74.2` release-control proved the release-validation groups passed, but the live browser full-test still failed in `project_source_remove_text` while `add_project_source` legitimately still owned the shared browser profile.

The failure was not a scheduler bypass:

```text
scheduler_path=shared_profile_async_lock
bypass_detected=false
active_operation=add_project_source
operation=remove_project_source
queue_timeout_seconds=120.0
```

The defect was that the full integration harness still used a hard-coded 120 second source-mutation wait budget, while the universal browser-operation scheduler default is 600 seconds.

## Scope

Changed:

```text
promptbranch_full_integration_test.py
tests/test_full_integration_harness.py
docs/repair-v0.1.74.3.md
docs/project/definition-of-done.md
docs/project/plan.md
docs/project/status.md
docs/project/release-status.md
docs/project/decisions.md
VERSION
pyproject.toml
promptbranch_version.py
tests/test_promptbranch_version.py
```

## Behavior

The full integration harness now derives `SOURCE_MUTATION_PROFILE_WAIT_SECONDS` from the same scheduler/profile-lock configuration surface:

```text
PROMPTBRANCH_SOURCE_MUTATION_PROFILE_WAIT_SECONDS
PROMPTBRANCH_BROWSER_PROFILE_LOCK_WAIT_SECONDS
CHATGPT_BROWSER_PROFILE_LOCK_WAIT_SECONDS
fallback: 600.0
```

This aligns full-test source add/remove cleanup behavior with the universal same-profile browser-operation scheduler policy.

## Out of scope

- No production Project Source semantics changed.
- No artifact adoption/current semantics changed.
- No browser automation redesign.
- No broad timeout increase unrelated to source mutation scheduler alignment.
- No v0.1.75 scope advanced.

## Validation

Focused validation for this repair must include:

```text
python3 -m pytest -q tests/test_full_integration_harness.py -k "source_mutation or profile_wait or docker_service_adapter"
python3 -m pytest -q tests/test_promptbranch_test_suite.py tests/test_promptbranch_test_report.py tests/test_project_control_surface.py tests/test_promptbranch_version.py
python3 -m pytest -q tests/test_promptbranch_artifacts.py tests/test_promptbranch_cli.py -k "adopt or artifact_current or local_only or local_artifact_not_found or promptbranch_repo or baseline_status or mvp_status"
python3 -m pytest -q tests/test_promptbranch_automation_service.py tests/test_promptbranch_service_client.py tests/test_promptbranch_cli.py -k "scheduler or profile_busy or queue_wait or source_remove or cleanup or release_lifecycle_plan"
```

Full release-control and adoption/current evidence remain required before acceptance.
