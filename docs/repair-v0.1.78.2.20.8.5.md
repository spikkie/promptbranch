# Repair v0.1.78.2.20.8.5 — Project deletion cleanup-policy evidence label consistency

## Release

`v0.1.78.2.20.8.5`

## Base release

`v0.1.78.2.20.8.4`

## Reason

`v0.1.78.2.20.8.4` correctly froze ChatGPT Project deletion at every runtime layer and the fresh-project source-add test proved `destructive_action_executed=false`, but the browser-suite summary still emitted the stale top-level label `cleanup_policy="same_run_ephemeral_cleanup"` when cleanup was selected. That wording contradicted the immutable no-delete invariant and made operator evidence ambiguous.

## Scope

Repair-only evidence/status cleanup:

- Replace the full-integration top-level cleanup policy label with `no_project_delete_until_secure_protocol`.
- Replace the non-owned-project cleanup evidence label with `no_project_delete_until_secure_protocol`.
- Preserve the non-destructive retained-project cleanup behavior from `v0.1.78.2.20.8.4`.
- Rename the stale test symbol that carried the old cleanup-policy phrase.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `promptbranch_full_integration_test.py`
- `tests/test_project_delete_safety.py`
- `tests/test_promptbranch_version.py`
- `docs/repair-v0.1.78.2.20.8.5.md`
- `docs/project/definition-of-done.md`
- `docs/project/status.md`
- `docs/project/release-status.md`
- `docs/project/plan.md`
- `docs/project/decisions.md`
- `docs/project/migration.md`

## Validation

Focused validation performed:

```bash
python3 -m pytest -q \
  tests/test_full_integration_harness.py \
  tests/test_project_delete_safety.py \
  tests/test_promptbranch_version.py \
  tests/test_project_control_surface.py
```

Static checks performed:

```bash
python3 -m compileall -q .
bash -n chatgpt_claudecode_workflow_release_control.sh
grep -R "same_run_ephemeral_cleanup" -n promptbranch_full_integration_test.py tests/test_project_delete_safety.py
```

The grep check must return no executable-test-surface matches for the stale cleanup-policy phrase.

## Explicit non-advancement statement

This repair does not advance a normal slice or line. It changes only stale evidence wording and version/repair documentation on top of `v0.1.78.2.20.8.4`. Project deletion remains immutable-frozen.
