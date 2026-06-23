# Repair v0.1.84.5.10.1 — localhost/offline rate-limit cooldown retry denylist

## Baseline

- Base candidate: `chatgpt_claudecode_workflow-2_v0.1.84.5.10.zip`
- Repair version: `v0.1.84.5.10.1`
- Accepted/current status: not changed by this repair candidate

## Reason

A run-all background log proved real ChatGPT/browser 429 telemetry, but release-control applied the generic browser cooldown retry path to the `full_localhost` validation transport and printed a long wait warning such as `waiting 190s before retry`.

The telemetry can be real while still being out of scope for localhost/offline validation groups. Those groups must never sleep or retry because of live-browser cooldown evidence.

## Files changed

- `chatgpt_claudecode_workflow_release_control.sh`
- `tests/test_promptbranch_shell_scripts.py`
- `VERSION`
- `promptbranch_version.py`
- `pyproject.toml`
- `tests/test_promptbranch_version.py`
- `docs/project/status.md`
- `docs/project/plan.md`
- `docs/project/release-status.md`
- `docs/project/definition-of-done.md`
- `docs/project/decisions.md`
- `docs/project/migration.md`
- `docs/repair-v0.1.84.5.10.1.md`

## Change

- Adds `run_all_step_disallows_browser_rate_limit_retry`.
- Denies browser cooldown retry for localhost/offline release-validation step names including `full_localhost`.
- Makes `run_all_rate_limit_cooldown_sleep` return non-zero before parsing or sleeping when such a step is denied.
- Updates the full-transport and JSON-step retry call sites so a denied cooldown does not fall through into a retry command under `set +e`.
- Adds a regression test that verifies the denylist is checked before the generic `waiting ... before retry` warning and that the `full_${label}` call site is guarded.

## Validation performed

- `bash -n chatgpt_claudecode_workflow_release_control.sh`
- `python -m py_compile tests/test_promptbranch_shell_scripts.py`
- `pytest -q tests/test_promptbranch_shell_scripts.py::test_release_control_full_localhost_rate_limit_retry_is_denylisted_before_sleep`

## Validation not completed

- Full pytest suite was not run in this environment.
- Full release-control all-tests/adoption was not run.
- No Promptbranch Project Source mutation was performed.
- No artifact adoption/current mutation was performed.

## Scope confirmation

This is a repair-only candidate. It does not advance accepted-event ledger scope, does not change ChatGPT Project deletion policy, does not mutate Project Sources, does not adopt artifacts, does not deploy, and does not grant model execution authority.
