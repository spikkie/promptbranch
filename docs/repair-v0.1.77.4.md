# Repair Release v0.1.77.4

## Base release

```text
v0.1.77.3
```

## Repair version

```text
v0.1.77.4
```

## Reason

`v0.1.77.3` still failed release-control cleanup when ChatGPT rate-limit pressure left the exact temporary project resolvable by name but not removable through the normal sidebar path.

## Files changed

```text
VERSION
pyproject.toml
promptbranch_version.py
promptbranch_full_integration_test.py
promptbranch_browser_auth/client.py
chatgpt_browser_auth/client.py
tests/test_full_integration_harness.py
tests/test_project_resolve.py
tests/test_promptbranch_version.py
docs/repair-v0.1.77.4.md
docs/project/definition-of-done.md
docs/project/plan.md
docs/project/status.md
docs/project/release-status.md
docs/project/decisions.md
docs/project/migration.md
```

## Repair scope

```text
- no normal slice advanced
- no release line advanced
- no repo-loop behavior changed
- no registry/adoption behavior changed
- no Project Source upload behavior changed
```

## Changes

- Extended temporary-project cleanup retries under rate-limit telemetry.
- Derived retry delay from nested `resolve_project` rate-limit telemetry instead of only generic busy payload fields.
- Increased cleanup attempts for the full integration cleanup step from 3 to 5.
- Increased direct project page details-menu wait during removal.
- Added a final rate-limit modal clearance check before declaring the configured project absent from the sidebar.

## Validation performed

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/test_full_integration_harness.py tests/test_project_resolve.py -k 'cleanup or remove_project'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/test_promptbranch_version.py tests/test_project_control_surface.py
python3 -m compileall -q .
bash -n chatgpt_claudecode_workflow_release_control.sh
bash -n scripts/post-release-validation.sh
ZIP hygiene check
clean extraction focused validation
```

## Slice/line advancement confirmation

```text
No normal slice advanced.
No release line advanced.
This is a repair of the intended v0.1.77 release line only.
```
