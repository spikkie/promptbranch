# Repair v0.1.104.1 — project-remove frozen scheduler timeout repair

## Base release

- Failed normal candidate: `chatgpt_claudecode_workflow-2_v0.1.104.zip`
- Accepted/current baseline before repair: `chatgpt_claudecode_workflow-2_v0.1.103.zip`
- Repair candidate: `chatgpt_claudecode_workflow-2_v0.1.104.1.zip`

## Reason

Full release-control for `v0.1.104` failed in the required `browser_scheduler_source_lifecycle` group. The active nodeid was:

```text
tests/test_promptbranch_automation_service.py::test_project_remove_is_frozen_before_profile_scheduler
```

The test used an unbounded `browser_status()` polling loop while waiting for an active `add_project_source` operation. If scheduler state was delayed or stale, the node could hang until the 300-second release-validation group timeout.

## Repair

The fixture now uses an explicit bounded `asyncio.Event` start signal from the mocked `add_project_source` operation and wraps each awaited phase with `asyncio.wait_for`. On failure it cancels and drains the task before re-raising, so the release-validation group fails fast with local evidence instead of burning the group timeout.

## Scope confirmation

This repair does not advance the normal slice. `v0.1.104` remains the active normal slice: Sandbox mutation verification and rollback evidence gate. `v0.1.105` remains deferred.

No ChatGPT Project deletion is enabled. The project-remove operation remains fail-closed with `project_delete_disabled` before browser/profile scheduler execution.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `tests/test_promptbranch_automation_service.py`
- `tests/test_project_control_surface.py`
- project control-surface docs under `docs/project/`

## Validation

Focused validation must include the repaired nodeid and the full browser scheduler source-lifecycle nodeid set before full release-control/adoption.
