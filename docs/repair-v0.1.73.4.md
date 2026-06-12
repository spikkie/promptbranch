# Repair v0.1.73.4 — Focused Scheduler Test Isolation

## Base release

```text
chatgpt_claudecode_workflow-2_v0.1.73.1.zip
```

## Superseded repair candidates

```text
chatgpt_claudecode_workflow-2_v0.1.73.2.zip
chatgpt_claudecode_workflow-2_v0.1.73.3.zip
```

## Repair version

```text
v0.1.73.4
```

## Reason

The v0.1.73.3 release-control lifecycle completed with exit code 0, but a focused scheduler test failed when run from a real repository profile that still had an accepted/current baseline of v0.1.73.1. The failing test used the ambient `.pb_profile` state while constructing a synthetic v0.1.50 release-lifecycle plan.

That made the test environment-dependent: the scheduler-plan assertion could fail because release current reconciliation saw a stale ambient adopted baseline, not because the scheduler plan itself was invalid.

## Files changed

```text
VERSION
pyproject.toml
promptbranch_version.py
tests/test_promptbranch_cli.py
docs/repair-v0.1.73.4.md
docs/project/definition-of-done.md
docs/project/plan.md
docs/project/status.md
docs/project/release-status.md
docs/project/decisions.md
```

## Change summary

```text
- The scheduler release-lifecycle plan test now passes an isolated --profile-dir under tmp_path.
- Production release-lifecycle reconciliation semantics are unchanged.
- v0.1.73.3 scheduler/source-lifecycle changes are preserved.
- v0.1.73.2 JSON/reporting compatibility changes are preserved.
```

## Validation performed

```text
focused JSON-contract tests: passed
focused scheduler/source cleanup tests: passed
project/repo/control/version tests: passed
compileall: passed
package import/version smoke: passed
ZIP hygiene: passed
clean extraction focused validation: passed
```

## No slice advancement

```text
No normal release scope advanced.
No new v0.1.74 functionality added.
No Project Source semantics changed.
No browser scheduler production behavior changed beyond the v0.1.73.3 carried-forward repair.
```
