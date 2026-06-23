# Repair v0.1.84.5.9 — live Project ensure URL extraction and recovered-429 success handling

## Base release

```text
chatgpt_claudecode_workflow-2_v0.1.84.5.8.zip
```

## Repair version

```text
v0.1.84.5.9
```

## Reason

The `v0.1.84.5.8` full run reached `live_project_ensure` and `pb project-ensure` returned a functional success payload with `ok=true` and a valid `project_url`, but release-control still reported that no Project URL was returned and skipped the downstream live steps.

The failure was caused by brittle release-control extraction and status handling around `pb project-ensure` output. Browser/rate-limit telemetry and nested JSON objects may appear after the successful Project ensure payload, so the extractor must not blindly use the last JSON object in the log. In addition, recovered 429 telemetry must not block the live phase when `project-ensure` returned `ok=true` and a usable `project_url`.

## Scope

- Parse `project_url`, `resolved_project_home_url`, or `project_home_url` robustly from the intended `ensure_project` / `project_ensure` JSON payload.
- Avoid treating trailing nested telemetry JSON as the Project ensure result.
- If `pb project-ensure` exits non-zero but the log contains strict rate-limit evidence and a valid `ok=true` Project URL payload, continue with `verified_with_recovered_rate_limit` warning semantics.
- Export the shared live Project URL so `ask-live`, `visual-artifact-roundtrip`, and `release-live` can continue with `--conversation-url`.
- Keep fail-closed behavior for missing URL, malformed JSON, `ok=false`, non-rate-limit non-zero command exit, timeout, and unrecovered 429 without a usable Project URL.

## Files changed

```text
VERSION
pyproject.toml
promptbranch_version.py
chatgpt_claudecode_workflow_release_control.sh
tests/test_promptbranch_shell_scripts.py
tests/test_promptbranch_version.py
docs/repair-v0.1.84.5.9.md
docs/project/status.md
docs/project/plan.md
docs/project/definition-of-done.md
docs/project/release-status.md
docs/project/decisions.md
docs/project/migration.md
```

## Validation performed

Focused validation in the repair workspace:

```text
pytest -q tests/test_promptbranch_shell_scripts.py::test_release_control_live_project_ensure_accepts_recovered_rate_limit_with_project_url
pytest -q tests/test_promptbranch_shell_scripts.py::test_release_control_run_all_tests_continues_and_writes_final_report
pytest -q tests/test_promptbranch_shell_scripts.py::test_release_control_run_all_reuses_one_shared_live_project_url
pytest -q tests/test_promptbranch_shell_scripts.py::test_release_control_run_all_does_not_retry_recovered_rate_limited_step
pytest -q tests/test_promptbranch_shell_scripts.py::test_release_control_run_all_retries_unrecovered_rate_limited_step_once
pytest -q tests/test_promptbranch_shell_scripts.py::test_release_control_declares_browser_read_timeout_service_recovery tests/test_promptbranch_shell_scripts.py::test_release_control_retries_live_preflight_once_after_browser_read_timeout
pytest -q tests/test_promptbranch_version.py tests/test_project_control_surface.py
python3 -m compileall -q .
bash -n chatgpt_claudecode_workflow_release_control.sh
python3 promptbranch_cli.py orchestration validate-ledger --json
python3 promptbranch_cli.py artifact guard --zip chatgpt_claudecode_workflow-2_v0.1.84.5.9.zip --version v0.1.84.5.9 --json
```

## Explicit non-scope

This repair does not advance the accepted-event ledger line, add ledger writes, change Project Source mutation behavior, change artifact adoption/current semantics, deploy anything, execute model-proposed actions, or re-enable ChatGPT Project deletion.

## Slice advancement

No normal slice or line advances. This is a repair-only candidate on top of `v0.1.84.5.8`.
