# Repair Release v0.1.77.1

## Base release

```text
chatgpt_claudecode_workflow-2_v0.1.77.zip
```

## Repair version

```text
chatgpt_claudecode_workflow-2_v0.1.77.1.zip
```

## Reason

The v0.1.77 candidate was not adopted/current after live browser validation exposed two robustness defects around temporary project lifecycle management:

1. Project creation could fail when the ChatGPT create-project dialog kept the submit button disabled after the project name appeared filled.
2. Cleanup could classify `Could not find the configured project in the sidebar` as success without independently proving that the temporary project was absent, allowing leaked test projects to be hidden by cleanup success.

## Files changed

```text
promptbranch_browser_auth/client.py
chatgpt_browser_auth/client.py
promptbranch_full_integration_test.py
tests/test_full_integration_harness.py
tests/test_project_list_browser_client.py
tests/test_promptbranch_version.py
VERSION
pyproject.toml
promptbranch_version.py
docs/project/definition-of-done.md
docs/project/plan.md
docs/project/status.md
docs/project/release-status.md
docs/project/decisions.md
docs/project/migration.md
```

## Repair behavior

```text
Project create:
- wait for the create submit button to become enabled after filling the project name;
- if it stays disabled, refill the name, dispatch normal input/change behavior through the existing fill helper, tab out, re-resolve the submit button, and fail with a clear diagnostic if it still stays disabled;
- do not force-click or evaluate-click disabled submit buttons.

Project cleanup:
- a remove-project sidebar-not-found result is not treated as success by itself;
- cleanup only succeeds as idempotent/absent when `resolve_project(name=...)` independently confirms zero matches;
- if absence cannot be verified, cleanup fails and the release/test report surfaces an error.
```

## Scope confirmation

```text
No slice or line advanced.
No repo-loop compatibility semantics were changed.
No registry/adoption semantics were changed.
No Project Source upload behavior was changed.
No browser service API contract was broadened beyond diagnostics and robustness around project create/remove.
```

## Validation performed

```text
Focused project cleanup tests passed.
Focused create-project disabled-submit regression test passed.
Version tests passed.
Project control-surface tests passed.
Bash syntax checks passed.
Compileall passed.
Clean extraction validation passed.
```

## Validation still required

```text
Full release-control lifecycle must be run by the operator.
Adoption/current evidence must be provided before this repair is called accepted/current.
```
