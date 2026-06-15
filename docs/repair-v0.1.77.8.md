# Repair v0.1.77.8 — Docker-service cleanup retarget accepts explicit project URL

## Repair metadata

```text
base release: v0.1.77
previous repair candidate: v0.1.77.7
repair version: v0.1.77.8
artifact: chatgpt_claudecode_workflow-2_v0.1.77.8.zip
repair type: validation failure repair
slice advanced: no
normal line advanced: no
```

## Reason

`v0.1.77.7` full release-control still failed in `project_remove_cleanup`.

The cleanup retry loop retargeted to the exact resolved temporary project URL, but the Docker-service adapter methods did not accept a per-call `project_url`. The retry therefore could fall back to the adapter's stored project URL instead of sending the exact resolved URL through the HTTP service request.

## Files changed

```text
promptbranch_full_integration_test.py
tests/test_full_integration_harness.py
docs/project/definition-of-done.md
docs/project/plan.md
docs/project/status.md
docs/project/release-status.md
docs/project/decisions.md
docs/project/migration.md
VERSION
pyproject.toml
promptbranch_version.py
tests/test_promptbranch_version.py
```

## Changes

- `DockerServiceAdapter.remove_project(...)` now accepts optional `project_url`.
- `DockerServiceAdapter.resolve_project(...)` now accepts optional `project_url`.
- Adapter sync methods use the explicit per-call URL when supplied, otherwise the adapter default URL.
- Added a focused regression proving cleanup retry sends the resolved leaked-project URL through Docker-service adapter calls.

## Validation performed

```text
python3 -m pytest -q tests/test_full_integration_harness.py -k "cleanup or DockerServiceAdapter or project_remove"
python3 -m pytest -q tests/test_project_control_surface.py tests/test_promptbranch_version.py
python3 -m compileall -q .
bash -n chatgpt_claudecode_workflow_release_control.sh
bash -n scripts/post-release-validation.sh
```

## Validation not performed

```text
full release-control lifecycle
live browser full-test
adoption/current verification
```

## Scope confirmation

```text
no normal slice advanced
no release line advanced
no repo-loop behavior changed
no registry/adoption behavior changed
no Project Source upload behavior changed
```
