# Repair v0.1.84.5.5 — Release-control recovered-rate-limit retry suppression

## Base

- Accepted/current baseline before this repair line: `chatgpt_claudecode_workflow-2_v0.1.84.5.zip`
- Repair base candidate: `v0.1.84.5.4`
- Repair version: `v0.1.84.5.5`

## Reason

`v0.1.84.5.4` changed live-test command policy so recovered ChatGPT 429 telemetry can be reported as a verified warning instead of a hard command failure. The outer release-control shell still retained an older conservative retry rule: if a run-all step exited non-zero and its log contained any 429 evidence, release-control waited and retried the whole step.

That retry is wasteful and wrong when the browser already handled the modal in-place:

1. ChatGPT showed a recoverable `Too many requests` / 429 modal.
2. Browser code clicked `Got it`.
3. Browser code waited the configured cooldown.
4. The same browser operation continued.
5. Functional verification passed.

In that case, release-control should preserve telemetry, mark the step as recovered, and continue without replaying the whole step.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `chatgpt_claudecode_workflow_release_control.sh`
- `tests/test_promptbranch_shell_scripts.py`
- `tests/test_promptbranch_version.py`
- `docs/repair-v0.1.84.5.5.md`
- `docs/project/status.md`
- `docs/project/plan.md`
- `docs/project/definition-of-done.md`
- `docs/project/release-status.md`
- `docs/project/decisions.md`
- `docs/project/migration.md`

## Behavior

Release-control now detects recovered-rate-limit success in step logs. If a step exits non-zero only because rate-limit contamination was recorded, but the payload proves functional success and modal/cooldown recovery evidence, release-control:

- does not retry the whole step,
- records a warning,
- normalizes the step as recovered for the run-all summary,
- reports the status as `verified_with_recovered_rate_limit`, and
- keeps rate-limit telemetry available in the logs.

Unrecovered 429 evidence remains retryable/failing.

## Validation

Focused validation performed:

- `test_release_control_run_all_does_not_retry_recovered_rate_limited_step`
- `test_release_control_run_all_retries_unrecovered_rate_limited_step_once`
- `test_release_control_rate_limit_detection_is_strict_not_generic`
- `tests/test_promptbranch_version.py`
- `tests/test_project_control_surface.py`
- `python3 -m compileall -q .`
- `bash -n chatgpt_claudecode_workflow_release_control.sh`
- `python3 promptbranch_cli.py orchestration validate-ledger --json`
- Artifact Guardian

## Scope boundary

This repair does not enable Project deletion, does not add ledger writes, does not change Project Source mutation behavior, does not alter artifact adoption/current semantics, and does not introduce deployment or model-execution authority.

## Slice advancement

No normal slice advanced. This is a repair-only candidate.
