# Repair v0.1.84.5.10.3 — ask-live recovered-success summary classification

## Base release

```text
chatgpt_claudecode_workflow-2_v0.1.84.5.10.2.zip
```

## Repair version

```text
v0.1.84.5.10.3
```

## Reason

`v0.1.84.5.10.2` corrected the `full_localhost` browser-cooldown denylist and restored `full_direct` retry behavior, but the run-all summary still kept `ask_live` in `failed_steps` when the command payload reported `status=verified_with_recovered_rate_limit`, `ok=false`, and `functional_failure_count=0` with all expected sentinels verified. That is a recovered live-step classification defect, not proof of functional ask-live failure.

## Scope

- Keep the `full_localhost` / localhost / offline browser-cooldown retry denial intact.
- Keep `full_direct` / direct outside the localhost/offline hard denylist.
- Treat `test_ask_live` payloads with `status=verified_with_recovered_rate_limit`, acknowledged cooldown telemetry, `functional_failure_count=0`, and verified expected-sentinel steps as recovered success in the all-tests summary.
- Keep failed or missing functional ask-live proof release-blocking.
- Do not mask `full_direct` or `full_localhost` source-add timeout/rate-limit failures.

## Files changed

```text
VERSION
pyproject.toml
promptbranch_version.py
chatgpt_claudecode_workflow_release_control.sh
tests/test_promptbranch_shell_scripts.py
tests/test_promptbranch_version.py
docs/project/status.md
docs/project/plan.md
docs/project/release-status.md
docs/project/definition-of-done.md
docs/project/decisions.md
docs/project/migration.md
docs/repair-v0.1.84.5.10.3.md
```

## Validation performed

```text
bash -n chatgpt_claudecode_workflow_release_control.sh
python -m py_compile tests/test_promptbranch_shell_scripts.py promptbranch_version.py
pytest -q -s tests/test_promptbranch_shell_scripts.py::test_release_control_all_tests_summary_accepts_ok_false_verified_recovered_ask_live_payload
pytest -q -s tests/test_promptbranch_shell_scripts.py::test_release_control_all_tests_summary_rejects_verified_recovered_ask_live_with_functional_failure
pytest -q -s tests/test_promptbranch_shell_scripts.py::test_release_control_all_tests_summary_prefers_top_level_recovered_ask_live_payload
pytest -q -s tests/test_promptbranch_shell_scripts.py::test_release_control_run_all_does_not_retry_recovered_rate_limited_step
pytest -q -s tests/test_promptbranch_shell_scripts.py::test_release_control_full_localhost_rate_limit_retry_is_denylisted_before_sleep tests/test_promptbranch_version.py tests/test_project_control_surface.py
```

## Validation not performed

```text
full pytest suite
full release-control --run-all-tests
install-from-ZIP validation
artifact adoption/current verification
```

## Explicit no-advance confirmation

This is a repair-only candidate. It does not advance the normal release line, accepted-event ledger/write scope, Project Source mutation scope, artifact adoption/current state, deployment behavior, ChatGPT Project deletion behavior, or model execution authority.
