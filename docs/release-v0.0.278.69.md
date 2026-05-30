# Release v0.0.278.69 — ask-live temporary project isolation

## Scope

Repair the `pb test ask-live --json` profile so the visible/local operator workflow does not run against the operator's active project or task by default.

## Changes

- `pb test ask-live` now creates an isolated temporary ChatGPT Project by default.
- The temporary project defaults to `ask-live-temp-<run-id>`.
- Ask steps are explicitly targeted at the temporary project URL.
- Every ask-live step verifies that the returned conversation belongs to the expected temporary project.
- The temporary project is removed after the run unless `--keep-project` is supplied.
- Operator state is restored after cleanup when a remembered workspace/task existed before the test.
- Added metadata fields to the JSON result:
  - `uses_temporary_project`
  - `test_project_name`
  - `test_project_url`
  - `test_project_created`
  - `test_project_removed`
  - `test_project_kept`
  - `test_project_setup`
  - `test_project_cleanup`
- Added CLI options:
  - `--project-name`
  - `--project-name-prefix`
  - `--memory-mode default|project-only`
  - `--project-icon`
  - `--project-color`
  - `--keep-project`

## Non-goals

- No changes to the repaired `pb ask` fill/submit logic.
- No release-control integration for `--run-ask-live-tests` yet.
- No artifact-download-live profile yet.

## Validation

Focused validation should cover parser dispatch, temp-project creation/removal behavior with a fake backend, compile checks, and the packaged ZIP hygiene check.
