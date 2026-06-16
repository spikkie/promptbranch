# Repair v0.1.78.2.3 — Retained quarantine project for delete-frozen release tests

## Problem

`v0.1.78.2.2` release-control completed with `exit_code: 0`, but the live full test created a unique project such as `itest-promptbranch-20260616-233235-4193168`. Cleanup reported `project_remove_cleanup_skipped_delete_frozen`, `destructive_action_executed=false`, and `postcondition=temporary_project_retained_delete_frozen`. This was safe, but it would leak one undeletable test project per release-control run.

## Change

Release-control now invokes:

```text
pb test full --project-name itest-promptbranch-retained-delete-frozen --keep-project --json
```

The retained project name can be overridden with `PROMPTBRANCH_RELEASE_TEST_PROJECT_NAME`, but the default is stable. Repeated release-control runs therefore reuse one quarantine project instead of creating a new unique project every time.

## Safety boundary

ChatGPT Project deletion remains frozen. This repair does not delete existing `itest-promptbranch-*` projects and does not implement a secure delete protocol. Project Source add/remove behavior remains unchanged.

## Validation

Focused shell tests assert the release-control command includes the retained quarantine project and `--keep-project`. Version, project-control, compile, bash syntax, and artifact-guardian checks must pass before operator release-control.
