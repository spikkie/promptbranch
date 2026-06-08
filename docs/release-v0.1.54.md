# Release v0.1.54

## Summary

Consolidate the JSON Orchestration State MVP design/control surfaces under `docs/design/orchestration/` and refresh the Promptbranch MVP living design so `docs/design/` is the canonical design home.

## Base

```text
chatgpt_claudecode_workflow-2_v0.1.53.zip
```

## Changes

- Moved the root-level `orchestration/` design/control tree to `docs/design/orchestration/`.
- Updated orchestration validators to read schemas/examples/state machines from the consolidated design path.
- Updated orchestration tests to assert the new canonical path.
- Refreshed `docs/design/promptbranch-mvp-living-design.md` for `v0.1.54`.
- Added `docs/design/promptbranch-mvp-gap-analysis.md`.
- Updated `docs/design/orchestration/docs/current_status.md` through the accepted `v0.1.53` baseline and the `v0.1.54` consolidation slice.

## Non-goals

- No runtime orchestration engine.
- No Kubernetes game implementation.
- No source-sync behavior change.
- No artifact adoption behavior change.
- No backend diagnostic behavior change.
- No version-source behavior change.

## Validation

```bash
python3 scripts/orchestration/validate_examples.py
python3 scripts/orchestration/validate_grill.py
python3 -m pytest -q tests/orchestration/test_orchestration_examples.py tests/orchestration/test_orchestration_grill_schema.py
python3 -m pytest -q tests/test_promptbranch_cli.py -k docs_status
python3 -m compileall -q .
pb release docs-status --version v0.1.54 --json
```
