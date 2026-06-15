# Repair v0.1.77.10 — version-pinned Docker service image selection

```text
base release: v0.1.77
previous failed repair: v0.1.77.9
repair version: v0.1.77.10
artifact: chatgpt_claudecode_workflow-2_v0.1.77.10.zip
release type: repair
normal slice advanced: no
line advanced: no
```

## Reason

`v0.1.77.9` release-control failed before the full browser test suite. The install ZIP and Project Source add succeeded, but Docker service recreation/version verification failed: the service endpoint continued to report `0.1.77.8` while the release expected `0.1.77.9`, even after the no-cache rebuild fallback.

The likely failure mode is a stale Docker Compose image reference or environment override taking precedence over the release-derived image tag.

## Files changed

```text
chatgpt_claudecode_workflow_release_control.sh
run_chatgpt_service.sh
run_chatgpt_service_dev.sh
tests/test_promptbranch_shell_scripts.py
docs/project/definition-of-done.md
docs/project/plan.md
docs/project/status.md
docs/project/release-status.md
docs/project/decisions.md
docs/project/migration.md
VERSION
pyproject.toml
promptbranch_version.py
```

## Change

Release-control and service start scripts now pin the Docker Compose service image to the release-derived image reference by default:

```text
promptbranch-service:<VERSION without leading v>
```

An explicit `PROMPTBRANCH_SERVICE_IMAGE` override is ignored during normal release-control unless `PROMPTBRANCH_ALLOW_SERVICE_IMAGE_OVERRIDE=1` is set. This prevents stale shell environment from silently selecting an older service image during release validation.

## Validation performed

```text
Focused shell-script tests for Docker service image/version behavior passed.
Project control-surface and version tests passed.
compileall passed.
bash syntax passed.
release import-plan validation passed.
ZIP hygiene passed.
```

## Validation not performed

```text
Full release-control lifecycle was not run by ChatGPT for v0.1.77.10.
Live browser full-test was not run by ChatGPT for v0.1.77.10.
No adoption/current evidence exists for v0.1.77.10.
```

## Scope confirmation

```text
No normal slice advanced.
No release line advanced.
No repo-loop behavior changed.
No registry/adoption behavior changed.
No Project Source upload behavior changed.
No browser cleanup behavior changed beyond the existing repair line.
```
