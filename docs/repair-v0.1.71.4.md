# Repair v0.1.71.4 — Service health version normalization

## Base release

```text
chatgpt_claudecode_workflow-2_v0.1.71.3.zip
```

## Repair version

```text
v0.1.71.4
```

## Reason

The v0.1.71.3 release lifecycle reached a healthy Promptbranch service, but the service wait gate compared the expected bare package version to the canonical service version without normalization:

```text
expected: 0.1.71.3
got:      v0.1.71.3
```

The health JSON contained:

```json
{
  "http_status": 200,
  "ok": true,
  "service": "promptbranch-service",
  "version": "v0.1.71.3"
}
```

This is a format mismatch, not a stale Docker service.

## Files changed

```text
VERSION
pyproject.toml
promptbranch_version.py
chatgpt_claudecode_workflow_release_control.sh
tests/test_promptbranch_shell_scripts.py
docs/project/definition-of-done.md
docs/project/plan.md
docs/project/status.md
docs/project/release-status.md
docs/project/decisions.md
docs/repair-v0.1.71.4.md
```

## Scope confirmation

This is a narrow repair. It does not advance the v0.1.71 normal slice, does not add release-set orchestration, does not change project-registry behavior, and does not change artifact adoption semantics.

## Behavior change

```text
release-control service health comparison now normalizes one leading `v`
`package_version` is preferred when present in health JSON
`version` is used as fallback
v-prefixed and bare versions compare equal when their normalized value matches
```

## Validation

```text
focused shell-script regression tests passed
project control-surface tests passed
compileall passed
clean extraction focused validation passed
ZIP hygiene passed
```

## Full-test status

```text
Full test suite was not run for this repair candidate.
```
