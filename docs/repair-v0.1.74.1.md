# Repair v0.1.74.1 — Release-validation pytest runner isolation

## Base release

```text
accepted/current baseline: chatgpt_claudecode_workflow-2_v0.1.73.4.zip
normal candidate repaired: chatgpt_claudecode_workflow-2_v0.1.74.zip
repair artifact: chatgpt_claudecode_workflow-2_v0.1.74.1.zip
```

## Reason

`v0.1.74` added first-class release-validation groups to `pb test full`, but the release-control run failed because those groups executed pytest through the installed Promptbranch entrypoint interpreter:

```text
/home/spikkie/.local/share/pipx/venvs/promptbranch/bin/python: No module named pytest
```

That interpreter is the runtime CLI environment and may intentionally not contain developer/test dependencies. Release-validation groups are repository validation commands, so they must default to the operator/repo Python instead of `sys.executable`.

## Files changed

```text
promptbranch_test_suite.py
tests/test_promptbranch_test_suite.py
VERSION
pyproject.toml
promptbranch_version.py
docs/repair-v0.1.74.1.md
docs/project/definition-of-done.md
docs/project/plan.md
docs/project/status.md
docs/project/release-status.md
docs/project/decisions.md
```

## Change summary

```text
- Add release-validation Python resolution helper.
- Default release-validation pytest/compileall commands to `python3`.
- Support `PROMPTBRANCH_RELEASE_VALIDATION_PYTHON` override for operators.
- Resolve placeholder commands at execution and manifest/report time.
- Add focused tests for default and override command resolution.
```

## Validation performed

```text
focused release-validation/test-report/control/version tests
artifact JSON contract focused tests
scheduler/source lifecycle focused tests
project/repo/control/version tests
compileall
package import/version smoke
ZIP hygiene
clean extraction focused validation
```

## Scope control

```text
No normal v0.1.75 scope advanced.
No browser automation behavior changed.
No artifact adoption/current semantics changed.
No Project Source semantics changed.
No deployment/Docker behavior changed.
```
