# Release v0.0.266 — Finalizer Failure Classification

## Baseline

Built from `chatgpt_claudecode_workflow_v0.0.265.zip`.

## Scope

This is a narrow finalizer diagnostics release. It does not add new mutation behavior or advance the native lifecycle engine.

## Changes

- Added structured finalizer/post-release validation classification to `scripts/post-release-validation.sh`.
- The post-release summary now includes:
  - `validation_classification`
  - `primary_failure_category`
  - `blocking_failure_categories`
- Classified blocking failures into stable operator-facing categories such as:
  - `product_validation_failure`
  - `artifact_hygiene_failure`
  - `artifact_state_failure`
  - `service_network_failure`
  - `protocol_contract_failure`
  - `artifact_intake_failure`
  - `artifact_candidate_lifecycle_failure`
  - `operator_precondition_failure`
- Preserved non-blocking pre-adoption baseline mismatch as `artifact_state_diagnostic` unless `--require-adopted-baseline` is requested.
- Added focused tests for:
  - strict real-candidate/no-artifact classification as `operator_precondition_failure`
  - unadopted baseline mismatch classification as non-blocking diagnostic

## Validation

- `python3 -m compileall -q .`
- `pytest -q tests/test_cli_parser.py`
- `pytest -q tests/test_promptbranch_cli.py`
- `pytest -q tests/test_promptbranch_mcp.py`
- Focused post-release validation classification tests:
  - `test_post_release_validation_classifies_strict_no_artifact_as_operator_precondition`
  - `test_post_release_validation_classifies_unadopted_baseline_as_diagnostic`
  - `test_post_release_validation_adopt_if_accepted_runs_protocol_after_adoption`

## Non-goals

- No lifecycle behavior consolidation.
- No new browser automation.
- No Project Source mutation.
- No Git commit/push automation changes.
- No write-capable agent or skill behavior.
