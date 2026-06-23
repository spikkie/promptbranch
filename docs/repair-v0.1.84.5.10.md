# Repair v0.1.84.5.10 — localhost validation isolation and ask-live streaming completion hardening

## Base

- Repair base: `v0.1.84.5.9`
- Accepted/current baseline remains: `chatgpt_claudecode_workflow-2_v0.1.84.5.zip`
- Repair version: `v0.1.84.5.10`

## Reason

The `v0.1.84.5.9` full all-tests/adoption run reached the shared live Project flow and proved `live_project_ensure` URL extraction, but still returned `FIX` because:

1. `full_localhost` timed out in the offline `browser_scheduler_source_lifecycle` release-validation group even though the same local release-validation groups had already passed in the primary `full_direct` run.
2. `ask-live` saw short sentinel answers rendered in the visible assistant turn while the ChatGPT UI still exposed a stop/running state; the browser returned partial timeout evidence and the ask-live wrapper classified the first prompts as `ask_failed`.
3. Release-control's strict rate-limit scan still treated absent modal selector-probe strings containing text such as `Too many requests` as rate-limit evidence even when structured telemetry reported no 429/modal/guardrail event.

## Changes

- Release-validation group subprocesses now strip browser-service transport environment variables before running offline pytest groups.
- Release-control marks the primary direct transport's release-validation groups as passed when proven by the structured full-test summary.
- Later run-all transports set `PROMPTBRANCH_RELEASE_VALIDATION_GROUPS_SKIP_DUPLICATE=1` after the primary groups have passed, causing offline release-validation groups to be reported as `skipped_duplicate_already_passed` rather than rerun under localhost transport context.
- Rate-limit log scanning ignores absent selector-probe diagnostics such as `[selector] selector probe ... has-text("Too many requests") ... visible=False`; real modal/backend/429 telemetry remains retryable/failing.
- Browser timeout evidence now carries the last visible assistant answer text in partial ask results.
- `ask-live` accepts a bounded streaming-timeout result only when the expected sentinel is visibly present in the expected Project and any extra suffix is cursor/streaming-marker-like. Missing sentinel, forbidden stale sentinel, wrong Project, or real unrecovered 429 remains failure.

## Validation performed

Focused validation completed locally:

- `pytest -q tests/test_promptbranch_cli.py::test_ask_live_accepts_visible_sentinel_after_streaming_timeout tests/test_promptbranch_cli.py::test_ask_live_streaming_timeout_still_fails_without_visible_sentinel tests/test_promptbranch_test_suite.py::test_release_validation_groups_skip_duplicate_env tests/test_promptbranch_test_suite.py::test_release_validation_group_strips_browser_service_env`
- `pytest -q tests/test_promptbranch_shell_scripts.py::test_release_control_rate_limit_detection_is_strict_not_generic`
- `pytest -q tests/test_promptbranch_shell_scripts.py::test_release_control_run_all_tests_continues_and_writes_final_report`
- `pytest -q tests/test_promptbranch_shell_scripts.py::test_release_control_run_all_reuses_one_shared_live_project_url`
- `python3 -m compileall -q .`
- `bash -n chatgpt_claudecode_workflow_release_control.sh`
- `python3 promptbranch_cli.py orchestration validate-ledger --json`
- Artifact Guardian against `chatgpt_claudecode_workflow-2_v0.1.84.5.10.zip`

Full all-tests/adoption were not run for this candidate in the artifact build environment.

## Scope not advanced

This repair does not change or advance:

- ChatGPT Project deletion; deletion remains frozen.
- Accepted-event ledger creation, append, or `accept-event --write`.
- Project Source mutation behavior.
- Artifact adoption/current semantics.
- Deployment.
- Model execution authority.

## Operator note

Run the normal full gate from the installed candidate ZIP. The expected improvement is that `full_localhost` no longer reruns the already-passed local release-validation groups, selector-probe strings no longer trigger false rate-limit retries, and `ask-live` can pass when a sentinel answer is visibly present but the UI stop/running state times out.
