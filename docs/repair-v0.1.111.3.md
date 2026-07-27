# Repair v0.1.111.3

## Normalised browser progress and genuine step-level fail-fast

The partial `v0.1.111.2` strict log had no terminal suite or adoption result. It nevertheless exposed two deterministic control defects: `project_not_found` was emitted as failed before being converted to the expected pre-create state, and `--fail-fast` was evaluated only after the entire browser integration phase returned.

### Contract

1. Apply expected-result normalisation before storing the `StepResult` and before emitting the terminal progress event.
2. `project_not_found` with `match_count=0` becomes `expected_missing`, remains `service_ok=false`, and counts as passed.
3. Propagate `fail_fast` into the browser integration harness.
4. After a genuinely failed normalised main browser step, record the failure and return `status=failed_fast` before the next main browser step starts.
5. Preserve bounded failure diagnostics for text-source mutation before terminating.
6. Mark all remaining browser/agent/release-validation units skipped so terminal progress is complete.
7. Preserve full direct, independent localhost, external-live, publication, Artifact Guardian, adoption, and accepted/current gates.
8. Do not add a global release-controller fast-stop option in this repair.
