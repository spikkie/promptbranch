# Repair v0.1.78.2.20.7 — Project Source text-add contract split

## Base release

`v0.1.78.2.20.6`

## Repair version

`v0.1.78.2.20.7`

## Reason

The focused `.20.6` Project Source text-add rerun proved the text source save path and post-refresh persistence path were healthy, but the visible Project Sources card still resolved to `pasted.txt Document` rather than a dedicated/generated filename. The `.20.6` dedicated-name requirement was therefore too strict for the Project Sources Text input surface.

This repair separates the release-blocking Project Sources text-add contract from large-paste/document-conversion characterization:

- Release-blocking `project_source_add_text` verifies the Text input source-add/persistence path with a below-threshold text body.
- Large pasted text conversion remains diagnostic/characterization evidence only.
- `pasted.txt Document` is not treated as current-run content proof, but it no longer blocks a source add that already has verified persistence.

## Scope

In scope:

- Keep `.20.3` large prompt-file attachment behavior unchanged.
- Keep `.20.4`/`.20.6` Project Source save/persistence diagnostics.
- Stop requiring a dedicated/generated document name as a release-blocking condition after persistence has been verified.
- Make full integration `project_source_add_text` use a smaller text body below the configured document-conversion threshold.
- Preserve legacy/generic document diagnostics as characterization fields.

Out of scope:

- CV generator changes.
- Prompt-file transport changes.
- Release-control adoption behavior changes.
- Artifact registry changes.
- Project deletion changes.
- Opening normal `v0.1.79` scope.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `promptbranch_full_integration_test.py`
- `promptbranch_browser_auth/client.py`
- `tests/test_project_source_capabilities.py`
- `tests/test_promptbranch_version.py`
- `docs/repair-v0.1.78.2.20.7.md`
- `docs/project/definition-of-done.md`
- `docs/project/status.md`
- `docs/project/release-status.md`
- `docs/project/decisions.md`
- `docs/project/migration.md`

## Validation performed

Focused local validation:

```bash
python3 -m py_compile promptbranch_browser_auth/client.py promptbranch_full_integration_test.py promptbranch_version.py
python3 -m pytest -q tests/test_project_source_capabilities.py tests/test_project_resolve.py tests/test_promptbranch_version.py tests/test_project_control_surface.py
```

Expected result: focused tests pass.

## Validation not performed

- Live focused Project Sources repro was not run here.
- Full release-control was not run here.
- Adoption/current verification was not run here.
- Full pytest was not run here.

## Line/slice movement

No normal slice or release line advanced. This is a repair-only candidate on the `.20.x` repair chain.
