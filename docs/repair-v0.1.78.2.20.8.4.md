# Repair v0.1.78.2.20.8.4 — Immutable Project deletion freeze

## Release

`v0.1.78.2.20.8.4`

## Base candidate

`v0.1.78.2.20.8.3`

## Reason

`v0.1.78.2.20.8.3` reintroduced a real ChatGPT Project deletion path through the same-run ephemeral cleanup exception. That exception is unsafe: a targeting, slug, URL-normalization, or stale state defect can turn a test cleanup into deletion of the operator's real ChatGPT Project.

## Repair scope

- Treat `NEVER delete ChatGPT Projects` as an immutable Promptbranch invariant.
- Block `/v1/projects/remove` at the container API before service resolution for every request.
- Block `ChatGPTAutomationService.remove_project` before lock acquisition or bot creation for every request.
- Block `ChatGPTBrowserClient.remove_project` before browser context creation for every request.
- Block the private browser `_remove_project_operation` as defense in depth if older wrappers or tests reach it.
- Make full-integration project cleanup non-destructive and retained-project only, without calling a lower-layer remove operation.
- Keep same-run identity fields as diagnostics only; they never authorize deletion.
- Preserve the intended text-source post-commit Project Sources recovery from `v0.1.78.2.20.8.3`.

## Out of scope

- Secure delete protocol design.
- Any Project Source add/remove semantic change beyond preserving the `v0.1.78.2.20.8.3` text-source recovery.
- Artifact adoption/current mutation.
- Normal `v0.1.79` work.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `promptbranch_project_delete_safety.py`
- `promptbranch_browser_auth/client.py`
- `promptbranch_automation/service.py`
- `promptbranch_container_api.py`
- `promptbranch_full_integration_test.py`
- `tests/test_project_delete_safety.py`
- `tests/test_full_integration_harness.py`
- `tests/test_project_resolve.py`
- `tests/test_promptbranch_version.py`
- `docs/project/definition-of-done.md`
- `docs/project/plan.md`
- `docs/project/status.md`
- `docs/project/release-status.md`
- `docs/project/decisions.md`
- `docs/project/migration.md`

## Validation performed

- Focused delete-safety tests.
- Focused full-integration cleanup tests.
- Focused browser private remove-operation test.
- Version test.
- Project control-surface test.
- Python compile check.
- ZIP hygiene check.

## Validation not performed

- Live browser release-control was not run in this build environment.
- Full test suite was not run.
- Artifact adoption/current was not performed.

## Explicit invariant

```text
No Promptbranch code path may click, confirm, or otherwise execute ChatGPT Project deletion.
```

`allow_ephemeral_test_cleanup=True` is retained only as diagnostic input compatibility. It is ignored as authorization and must produce a blocked/delete-frozen payload.

## Slice advancement

No normal slice or line advanced. This is a repair-only release.
