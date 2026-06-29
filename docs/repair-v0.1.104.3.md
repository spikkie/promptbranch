# Repair v0.1.104.3 — remove isolated release-test mode

## Base release

- Accepted/current baseline before repair: `chatgpt_claudecode_workflow-2_v0.1.103.zip`
- Failed normal candidate: `chatgpt_claudecode_workflow-2_v0.1.104.zip`
- Failed repair candidates: `chatgpt_claudecode_workflow-2_v0.1.104.1.zip`, `chatgpt_claudecode_workflow-2_v0.1.104.2.zip`
- Repair candidate: `chatgpt_claudecode_workflow-2_v0.1.104.3.zip`

## Reason

The isolated release-test mode added in `v0.1.104.2` introduced a second validation control path and caused confusion during operator runs. The operator chose to remove that path and continue using focused local checks only during artifact creation, with full release-control as the only acceptance/adoption gate.

A pasted full-test run also showed stale operator variables installing `v0.1.104.1` instead of the intended `v0.1.104.2`; this repair makes the recommended path unambiguous by removing the isolated flag entirely.

## Repair

- Remove `--run-isolated-release-tests` and `--run-slice-tests` parsing from `chatgpt_claudecode_workflow_release_control.sh`.
- Remove the isolated release-test runner and summary schema from release-control.
- Add regression coverage proving the isolated mode is absent.
- Preserve the `v0.1.104.2` Project ensure timeout and post-timeout exact-resolve recovery behavior.
- Preserve the `v0.1.104.1` project-remove frozen scheduler timeout repair.
- Preserve the `v0.1.104` sandbox mutation verification and rollback evidence gate.

## Scope confirmation

This repair does not advance the normal slice. `v0.1.104` remains the active normal slice: Sandbox mutation verification and rollback evidence gate. `v0.1.105` remains deferred.

No ChatGPT Project deletion is enabled. The no-delete invariant remains active.

## Validation

Focused validation must prove the release-control script no longer exposes isolated release-test flags, the Project ensure timeout repair tests still pass, the sandbox verification smoke still passes, Artifact Guardian passes, and ZIP hygiene is clean. Full release-control/adoption remains required before this repair can be called accepted/current.
