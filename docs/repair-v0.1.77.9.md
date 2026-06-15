# Repair v0.1.77.9 — source-save stale-inflight proof and cleanup project-name forwarding

## Base release

```text
v0.1.77.8
```

## Repair version

```text
v0.1.77.9
```

## Reason

`v0.1.77.8` release-control still failed before adoption. The live browser run showed two remaining repair-line defects:

1. Text Project Source add failed after seeing a commit and a visible source card because one relevant save request remained stale/inflight.
2. Temporary project cleanup could resolve the exact leaked project by name and URL, but remove retry still lacked a project-name fallback through the Docker service and browser-client removal path.

## Files changed

```text
VERSION
pyproject.toml
promptbranch_version.py
promptbranch_browser_auth/client.py
promptbranch_container_api.py
promptbranch_automation/automation.py
promptbranch_automation/service.py
promptbranch_full_integration_test.py
promptbranch_service_client.py
tests/test_project_source_capabilities.py
tests/test_full_integration_harness.py
tests/test_promptbranch_service_client.py
tests/test_promptbranch_version.py
docs/project/definition-of-done.md
docs/project/plan.md
docs/project/status.md
docs/project/release-status.md
docs/project/decisions.md
docs/project/migration.md
```

## Scope confirmation

```text
No normal slice advanced.
No release line advanced.
No repo-loop behavior changed.
No registry/adoption behavior changed.
No Project Source upload semantics were broadened beyond requiring post-refresh persistence verification.
```

## Validation performed

```text
Focused source-save quiet tests passed.
Focused cleanup/remove tests passed.
Service-client remove-project request tests passed.
Project control-surface and version tests passed.
compileall passed.
ZIP hygiene passed.
```
