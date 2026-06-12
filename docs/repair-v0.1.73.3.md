# Repair v0.1.73.3 — Universal browser-operation scheduler coverage

## Base release

```text
chatgpt_claudecode_workflow-2_v0.1.73.1.zip
```

## Repair version

```text
v0.1.73.3
```

## Reason

`v0.1.73.2` superseded the validation/reporting repair candidate but failed release-control with `browser_profile_busy` during live source/project cleanup. The failure showed that source remove and project cleanup paths still depended on shorter or uneven profile-lock waits instead of one universal scheduler-mediated browser-operation model.

## Files changed

```text
promptbranch_automation/service.py
promptbranch_browser_auth/exceptions.py
promptbranch_container_api.py
promptbranch_service_client.py
promptbranch_full_integration_test.py
promptbranch_cli.py
promptbranch_version.py
pyproject.toml
VERSION
tests/test_promptbranch_automation_service.py
tests/test_promptbranch_service_client.py
tests/test_promptbranch_cli.py
tests/test_project_control_surface.py
tests/test_promptbranch_version.py
docs/project/definition-of-done.md
docs/project/plan.md
docs/project/status.md
docs/project/release-status.md
docs/project/decisions.md
```

## Repair behavior

```text
- Default browser profile queue wait now matches the advertised scheduler model: 600 seconds.
- Source add, source remove, and project remove can use scheduler-aware profile lock waits.
- Docker service remove-source and remove-project requests accept profile_lock_wait_seconds.
- Full integration cleanup passes the source mutation wait budget into remove-source and project-remove calls.
- BrowserProfileBusyError payloads expose scheduler_path, queue_wait_seconds, queue_timeout_seconds, and bypass_detected.
- v0.1.73.2 JSON/reporting repair intent is carried forward: baseline_evidence compatibility, runtime-version test freshness, external repo registry/state alignment.
```

## Scope control

```text
No normal v0.1.74 scope advanced.
No Project Source semantics changed.
No broad profile-pool redesign.
No Docker/deployment behavior changed beyond passing scheduler-aware wait parameters through existing endpoints.
```

## Validation target

```text
focused scheduler tests
focused JSON-contract tests
project/repo/control/version tests
ZIP hygiene
clean extraction validation
full release-control by operator before adoption
```

## Slice/line confirmation

```text
repair release only; no slice or line advanced
```
