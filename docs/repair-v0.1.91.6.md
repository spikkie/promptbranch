# Repair v0.1.91.6 — Adopt-after-validation run-all evidence-reuse report path repair

## Type

Repair-only release.

## Base

- Accepted/current baseline before the repair stack: `chatgpt_claudecode_workflow-2_v0.1.91.1.zip`
- Repair stack preserved: `v0.1.91.2`, `v0.1.91.3`, `v0.1.91.4`, `v0.1.91.5`
- Immediate repair base: `chatgpt_claudecode_workflow-2_v0.1.91.5.zip`

## Reason

The `v0.1.91.5 --run-all-tests --adopt-after-validation` run reached `all_tests_final_verdict=GO`, but the adoption footer crashed while trying to read `pb_test.full.direct.<version>.report.json`.

That direct report file is intentionally absent when `--run-all-tests` reuses direct validation evidence. In that mode, the authoritative proof is the all-tests summary plus `validation_evidence/full_direct.<version>.json`.

## Scope

This repair changes only adoption verifier/report path selection after a green run-all summary.

## Files changed

- `chatgpt_claudecode_workflow_release_control.sh`
- `tests/test_promptbranch_shell_scripts.py`
- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `tests/test_promptbranch_version.py`
- `docs/project/status.md`
- `docs/project/release-status.md`
- `docs/project/definition-of-done.md`
- `docs/project/plan.md`
- `docs/project/decisions.md`
- `docs/project/migration.md`

## Behavior

When a direct full-test report exists, release-control continues to validate that report directly.

When `--run-all-tests` reuses direct evidence and the direct report file is absent, release-control validates:

1. `pb_test.all.<version>.summary.json` is green with `final_verdict=GO`.
2. `validation_evidence/full_direct.<version>.json` is present and still matches the expected artifact hash, version, transport, service base, runtime mode, strict matrix flag, command signature, and green test/report status.

If neither a green report nor valid reused evidence exists, adoption still fails closed.

## Out of scope

- No validation semantics change.
- No live/browser behavior change.
- No adoption/current semantic change.
- No Project Source mutation behavior change.
- No ChatGPT Project deletion behavior change.
- No deployment/Kubernetes behavior change.
- No normal slice advancement.

## Validation

Focused validation completed in the candidate build environment:

- adoption verifier contract for missing direct report plus reused direct evidence
- run-all evidence reuse/localhost audit regression
- pretty live JSON / live-step aggregation regression
- version tests
- project control-surface tests
- `compileall`
- shell syntax
- Artifact Guardian
- artifact verify
- ZIP hygiene

## Slice movement

No normal slice or line advanced. This repair only closes the adoption-footer defect discovered after `all_tests_final_verdict=GO` in `v0.1.91.5`.
