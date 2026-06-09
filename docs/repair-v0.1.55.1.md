# Repair v0.1.55.1

## Base release

`chatgpt_claudecode_workflow-2_v0.1.55.zip`

## Repair version

`v0.1.55.1`

## Reason

`v0.1.55` introduced read-only grill validation against the k8s-game MVP state machine. The validator correctly failed closed for invalid provider fixtures, but it could raise a Python traceback before returning structured `grill_invalid` JSON when the CLI was given a relative ad-hoc fixture such as `.tmp_validation/G0_bad_provider.example.json`, or an absolute fixture outside the repository.

Root cause: `scripts/orchestration/validate_grill.py` used `path.relative_to(ROOT)` directly on caller-supplied paths without first resolving them or allowing external fixture labels.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `scripts/orchestration/validate_grill.py`
- `tests/orchestration/test_orchestration_grill_schema.py`
- `docs/repair-v0.1.55.1.md`

## Validation performed

- `python3 scripts/orchestration/validate_examples.py`
- `python3 scripts/orchestration/validate_grill.py`
- repo-relative invalid provider fixture smoke
- external `/tmp` invalid provider fixture smoke
- `python3 -m pytest -q tests/orchestration/test_orchestration_examples.py tests/orchestration/test_orchestration_grill_schema.py`
- `python3 promptbranch_cli.py release docs-status --version v0.1.55.1 --json`
- `python3 -m compileall -q .`
- ZIP hygiene verification

## Scope confirmation

This is a repair-only release. It does not advance the JSON Orchestration State MVP slice, does not add accepted-event behavior, does not mutate runtime orchestration state, does not perform source/project mutation, and does not advance the release line beyond the intended `v0.1.55` behavior.
