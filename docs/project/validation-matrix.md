# Validation Matrix

## Purpose

This file defines the required release-validation groups for `pb test full` and release-control evidence.

`pb test full` must not rely on operator memory for focused regression suites. The full/release validation report must declare which groups ran, which groups were skipped, and whether skipped groups are allowed.

## Required release-validation groups

| Group | Required | Purpose | Representative command |
|---|---:|---|---|
| `project_control_surface` | yes | Validate `docs/project/` structure, DoD table, release-status table, and next safe action. | `python3 -m pytest -q tests/test_project_control_surface.py` |
| `version_surface` | yes | Validate `VERSION`, `pyproject.toml`, and `promptbranch_version.py` consistency. | `python3 -m pytest -q tests/test_promptbranch_version.py` |
| `artifact_json_contracts` | yes | Guard artifact adopt/current/baseline JSON contracts and external-repo reporting. | `python3 -m pytest -q tests/test_promptbranch_artifacts.py tests/test_promptbranch_cli.py -k "adopt or artifact_current or local_only or local_artifact_not_found or promptbranch_repo or baseline_status or mvp_status"` |
| `repo_project_registry` | yes | Guard project-scoped repo registry behavior and repo doctor/list invariants. | `python3 -m pytest -q tests/test_promptbranch_project.py tests/test_promptbranch_repos.py` |
| `browser_scheduler_source_lifecycle` | yes | Guard scheduler/source lifecycle behavior, same-profile queueing, browser busy diagnostics, and cleanup planning. | `python3 -m pytest -q tests/test_promptbranch_automation_service.py tests/test_promptbranch_service_client.py tests/test_promptbranch_cli.py -k "scheduler or profile_busy or queue_wait or source_remove or cleanup or release_lifecycle_plan"` |
| `release_lifecycle_plan` | yes | Guard release lifecycle plan and source queue integration invariants. | `python3 -m pytest -q tests/test_promptbranch_cli.py -k "release_lifecycle_plan"` |
| `package_import_smoke` | yes | Validate installed package imports outside the source tree. | `pb test full` agent profile step `package_import_smoke` |
| `compileall` | yes | Validate Python source compilation. | `python3 -m compileall -q .` |
| `zip_hygiene` | yes | Validate candidate ZIP layout and generated/cache exclusions. | `pb test full` agent profile step `package_hygiene` |

## Reporting rule

The full-test JSON and post-release validation summary must include:

```text
release_validation_groups.ok
release_validation_groups.missing_required_groups
release_validation_groups.groups.<group>.ok
release_validation_groups.groups.<group>.command
```

If a required group is missing or failed, release-control must treat the full-test evidence as not green.

## Last updated

```text
v0.1.74
```
