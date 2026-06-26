# Repair v0.1.91.9 — Adopt-after-validation localhost lifecycle-reuse report path repair

## Base

- Repair base: `chatgpt_claudecode_workflow-2_v0.1.91.8.zip`
- Accepted/current before this repair remains whatever the operator proves with `pb artifact current --json`; this candidate does not declare itself accepted/current.

## Reason

`v0.1.91.8 --run-all-tests --adopt-after-validation` reached `all_tests_final_verdict=GO`, but the adoption footer crashed because it still required `pb_test.full.localhost.<version>.report.json`. That file is intentionally absent when `full_localhost` reuses the direct browser/source lifecycle proof.

## Scope

This repair changes only adopt-after-validation report-path selection for the reused `full_localhost` lifecycle path and adds progress telemetry for long `--run-all-tests` runs.

Preserved behavior:

- `v0.1.91.8` single live browser/source lifecycle reuse.
- `v0.1.91.7` Docker no-cache build-context repair.
- `v0.1.91.6` direct evidence-reuse adoption report path repair.
- Live/browser behavior.
- Validation semantics.
- Adoption/current semantics.
- Project Source mutation semantics.
- ChatGPT Project deletion freeze.

## Changes

- Added `verify_reused_full_localhost_lifecycle_green`.
- Added `report_or_reused_full_localhost_lifecycle_green`.
- In `test_transport=both`, adoption verification accepts a missing localhost report only when:
  - `pb_test.all.<version>.summary.json` has `final_verdict=GO`.
  - `validation_evidence/full_direct.<version>.json` validates against artifact/version/hash/dimensions.
  - the all-tests summary contains `full_localhost` with `ok=true` and `status` or `action` equal to `reused_browser_source_lifecycle`.
- Added `all_tests_progress` console output and `pb_test.all.<version>.progress.json` after each run-all step, reporting tested/succeeded/failed counts and percentages.

## Validation performed before handoff

- Focused shell tests for localhost lifecycle-reuse adoption report path.
- Focused shell tests for run-all progress telemetry contract.
- Existing run-all/evidence reuse/localhost audit regression tests.
- Version tests.
- Project-control-surface tests.
- `compileall`.
- `bash -n chatgpt_claudecode_workflow_release_control.sh`.
- Artifact Guardian.
- ZIP hygiene/artifact verify.

## No slice advancement

This is a repair-only release. It does not advance the normal `v0.1.91` slice and does not open `v0.1.92`.
