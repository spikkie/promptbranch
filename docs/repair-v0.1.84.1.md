# Repair v0.1.84.1 — fresh live-test Project per run

## Base release

`v0.1.84` focused candidate.

## Repair version

`v0.1.84.1`

## Reason

Live/browser test runs reused one retained delete-frozen ChatGPT Project. Because Project deletion remains frozen, that retained Project accumulates conversations and source/test history. Subsequent Promptbranch browser operations then spend increasing time traversing existing Project data.

## Scope

Repair-only. No orchestration ledger scope advanced. No accepted-event write path was added.

## Changes

- Release-control now generates a fresh run-scoped `itest-promptbranch-<version>-<timestamp>-<pid>` Project name by default for each validation invocation.
- `pb test ask-live`, `pb test visual-artifact-roundtrip`, and `pb test release-live` now default to generated run-scoped Project prefixes instead of the old retained quarantine Project.
- `--keep-project` remains enforced because whole-project deletion is still frozen.
- Operators may still provide `--project-name` or `--conversation-url` explicitly.
- Tests were updated to verify dynamic run-scoped Project names and the new cleanup policy.

## Validation performed

- Parser/default live-test project prefix tests.
- ask-live unique delete-frozen Project unit test.
- release-control shell-script tests for generated per-run Project names.
- compileall and shell syntax checks.
- Artifact Guardian ZIP validation.

## No slice advancement

This repair does not advance beyond `v0.1.84` ledger validation. It fixes test-run Project isolation only. Accepted/current remains `v0.1.79` until promotion/adoption evidence exists.
