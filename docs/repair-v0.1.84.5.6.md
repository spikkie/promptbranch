# Repair v0.1.84.5.6 — test-all shared live Project reuse

## Classification

- Repair type: validation/runtime workflow repair only.
- Base candidate: `v0.1.84.5.5`.
- Repair version: `v0.1.84.5.6`.
- Accepted/current before repair remains: `chatgpt_claudecode_workflow-2_v0.1.84.5.zip`.
- No orchestration ledger/write slice advanced.

## Reason

`v0.1.84.5.1` introduced fresh Projects for live/browser test runs to avoid reusing one retained Project forever while deletion is frozen. That policy was too broad for `release-control --run-all-tests`: the full validation stack should not create a separate Project for each live subtest.

The desired release-control behavior is one run-scoped ChatGPT Project per `test-all` invocation, created/ensured once after live profile preflight, then reused by `ask-live`, `visual-artifact-roundtrip`, and `release-live` via exact Project URL.

## Changes

- Added `live_project_ensure` to release-control run-all live phase.
- Ensures `${release_test_project_name}` once through the authenticated seed profile.
- Extracts the returned `project_url` from the `project ensure` JSON output.
- Passes that URL to all live subtests with `--conversation-url`.
- Stops passing `--project-name` to individual live subtests in release-control run-all.
- Preserves delete-frozen semantics: the shared Project is retained.
- Preserves recovered-rate-limit retry suppression from `v0.1.84.5.5`.

## Explicit non-goals

- No Project deletion re-enable.
- No ledger creation or append.
- No `accept-event --write`.
- No Project Source mutation behavior change.
- No artifact adoption/current semantic change.
- No deployment or model-execution scope change.

## Validation

Focused validation performed for this repair:

- `bash -n chatgpt_claudecode_workflow_release_control.sh`
- `python3 -m py_compile promptbranch_cli.py`
- `python3 -m pytest -q tests/test_promptbranch_cli.py -k 'ask_live or visual_artifact_roundtrip or release_live or project_name_cap or unique_project'`
- `python3 -m pytest -q tests/test_promptbranch_shell_scripts.py::test_release_control_run_all_tests_continues_and_writes_final_report`
- `python3 -m pytest -q tests/test_promptbranch_shell_scripts.py::test_release_control_run_all_reuses_one_shared_live_project_url`
- `python3 -m pytest -q tests/test_promptbranch_shell_scripts.py::test_release_control_run_all_has_rate_limit_retry_policy_declared`
- `python3 -m pytest -q tests/test_promptbranch_shell_scripts.py::test_release_control_run_all_does_not_retry_recovered_rate_limited_step`

Full all-tests and adoption were not run in the artifact build environment.

## Expected operator proof

After install, release-control run-all logs should show exactly one shared live Project ensure step:

```text
== pb test-all step: live_project_ensure ==
reuse_policy: one_run_scoped_project_for_all_test_all_live_steps
shared_live_project_url: https://chatgpt.com/g/...
```

Subsequent live steps should use the shared URL:

```text
pb test ask-live ... --conversation-url <shared_live_project_url> --keep-project --json
pb test visual-artifact-roundtrip ... --conversation-url <shared_live_project_url> --keep-project --json
pb test release-live ... --conversation-url <shared_live_project_url> --keep-project --json
```

They should not each create their own Project during one release-control run-all invocation.
