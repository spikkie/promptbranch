# Repair v0.1.100.2 — browser scheduler source-lifecycle timeout repair

Base normal release: `v0.1.100`
Previous repair: `v0.1.100.1`
Repair version: `v0.1.100.2`

## Reason

`v0.1.100.1` full release-control failed in `full_direct` because the required offline `browser_scheduler_source_lifecycle` group timed out while running `tests/test_promptbranch_automation_service.py::test_source_remove_waits_behind_source_list_with_same_profile`.

## Scope

This repair preserves the `v0.1.100` first controlled read-only validation command execution behavior and the `v0.1.100.1` text-source stale-inflight diagnostics repair. It changes only the same-profile source-remove test fixture so it uses a bounded explicit start signal instead of an unbounded active-operation polling loop.

## No scope advancement

`v0.1.101` remains deferred. This repair does not add read-only command result diagnosis, correction planning, file mutation, deployment, Kubernetes mutation, Project Source behavior changes, artifact adoption behavior changes, or ChatGPT Project deletion.

## Validation

Focused validation must include the hanging nodeid, the release-validation group manifest, control-surface validation, version validation, compileall, shell syntax, Artifact Guardian, and artifact verify. Full acceptance still requires release-control `--run-all-tests --adopt-after-validation`.
