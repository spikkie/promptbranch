# Repair v0.1.78.2.20.4 — Project Source text document-conversion proof

## Base release

`chatgpt_claudecode_workflow-2_v0.1.78.2.20.3.zip`

## Repair version

`v0.1.78.2.20.4`

## Reason

The `v0.1.78.2.20.3` full release-control and focused repro both failed on `project_source_add_text` with `persistence_not_verified`. The valid focused repro resolved the retained test project and reached the Project Sources surface, but no save request was observed and the requested text source never appeared. The Project Sources surface already contained five stale retained-test sources, including generic `pasted.txt Document`, and the current ChatGPT UI can represent pasted text as a generated `.txt` document instead of a named text source.

## Scope

This repair changes only the Project Source text-add test/verification path:

- the live `project_source_add_text` test now uses a large run-id-bearing text body so the document-conversion path is exercised explicitly;
- large text-source match candidates include first-line/document filenames such as `Integration note for run ... .txt Document`;
- generic `pasted.txt Document` is not accepted as proof unless the generated document/card can be tied to the current run-id-bearing content;
- retained integration-test sources may be pruned at the observed five-source boundary, but only when the requested add is an integration-test text source and the prune candidate is clearly test-owned/generic (`itest-*`, `Integration note for run ...`, or `pasted.txt`).

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `promptbranch_browser_auth/client.py`
- `promptbranch_full_integration_test.py`
- `tests/test_project_source_capabilities.py`
- `tests/test_promptbranch_version.py`
- `docs/project/definition-of-done.md`
- `docs/project/status.md`
- `docs/project/release-status.md`
- `docs/project/decisions.md`
- `docs/project/migration.md`
- `docs/repair-v0.1.78.2.20.4.md`

## Validation performed

Focused validation was run locally:

```text
python3 -m py_compile promptbranch_browser_auth/client.py promptbranch_full_integration_test.py promptbranch_version.py
python3 -m pytest -q tests/test_project_source_capabilities.py tests/test_project_resolve.py
python3 -m pytest -q tests/test_promptbranch_version.py tests/test_project_control_surface.py
```

Full release-control and live browser validation were not run in this build environment.

## Slice/state confirmation

This is a repair release. It does not advance the normal release slice, open the v0.1.79 line, change project deletion policy, change artifact adoption/current semantics, or alter the already-working prompt-file attachment transport from v0.1.78.2.20.3.
