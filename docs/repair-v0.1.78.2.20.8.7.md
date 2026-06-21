# Repair v0.1.78.2.20.8.7 — Plain-text response wait deadline diagnostic guard

## Release

`v0.1.78.2.20.8.7`

## Base release

`v0.1.78.2.20.8.6`

## Reason

A live `pb ask`/browser-service run produced the requested plain-text sentinel answer, but the response wait loop continued because ChatGPT still exposed a running/stop-button state and no composer idle signal. While debug diagnostics were enabled and deadline budget was exhausted, `_wait_and_get_response()` attempted to set `breakdown["response_debug_artifact_skipped_due_to_deadline"] = True` even though the plain-text response wait path had not initialized `breakdown`.

That produced:

```text
NameError: name 'breakdown' is not defined
```

The JSON response wait path already initializes `response_wait_breakdown`; the plain-text path must do the same before any diagnostic/deadline bookkeeping branch can run.

## Scope

Repair-only response-wait diagnostic guard on top of `v0.1.78.2.20.8.6`:

- Initialize `response_wait_breakdown` at the start of `_wait_and_get_response()` when a response context is provided.
- Preserve existing plain-text completion semantics; do not weaken stop-button, idle, freshness, or stable-response predicates.
- Mark `response_debug_artifact_skipped_due_to_deadline` when debug artifact writing is skipped because deadline budget is exhausted.
- Add a focused regression test that exercises the deadline-exhausted debug-skip path and proves it does not raise `NameError`.
- Preserve the immutable no-delete invariant and the joined-repo state authority repair from `v0.1.78.2.20.8.6`.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `promptbranch_browser_auth/client.py`
- `tests/test_project_list_browser_client.py`
- `tests/test_promptbranch_version.py`
- `docs/repair-v0.1.78.2.20.8.7.md`
- `docs/project/definition-of-done.md`
- `docs/project/status.md`
- `docs/project/release-status.md`
- `docs/project/plan.md`
- `docs/project/decisions.md`
- `docs/project/migration.md`

## Validation

Focused validation performed:

```bash
python3 -m pytest tests/test_project_list_browser_client.py::test_wait_and_get_response_initializes_breakdown_for_debug_deadline_skip tests/test_project_list_browser_client.py::test_wait_and_get_json_skips_final_debug_when_hard_deadline_exhausted tests/test_promptbranch_version.py -q
```

Additional validation performed:

```bash
python3 -m pytest tests/test_project_list_browser_client.py::test_wait_and_get_response_initializes_breakdown_for_debug_deadline_skip tests/test_project_list_browser_client.py::test_wait_and_get_json_skips_final_debug_when_hard_deadline_exhausted tests/test_promptbranch_version.py tests/test_project_control_surface.py -q
python3 -m compileall -q .
bash -n chatgpt_claudecode_workflow_release_control.sh
```

Full release-control, live browser validation, and adoption/current verification were not run in this environment.

## Explicit non-advancement statement

This repair does not advance a normal slice or line. It changes only plain-text response-wait diagnostic bookkeeping, version metadata, a focused regression test, and repair documentation on top of `v0.1.78.2.20.8.6`. Project deletion remains immutable-frozen.
