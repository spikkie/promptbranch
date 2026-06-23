# Release v0.1.84.5.11 — live validation diagnostics and source-add timeout observability

## Baseline

- Baseline: `chatgpt_claudecode_workflow-2_v0.1.84.5.10.3.zip`
- Type: normal release slice from accepted repair baseline
- Target artifact: `chatgpt_claudecode_workflow-2_v0.1.84.5.11.zip`

## Scope

This slice adds release-control diagnostics only. It does not mask or auto-green live browser failures.

Included:

- Per-step all-tests diagnostics for transport class, rate-limit evidence, retry policy, retry denial, browser ReadTimeout evidence, source-add evidence, source-add timeout detection, likely failure phase, and next operator action.
- Full transport post-release summaries now carry `promptbranch.release_control.full_transport_diagnostics` so `full_direct` and `full_localhost` failures remain explainable from the all-tests summary.
- Fast fixture tests cover source-add ReadTimeout diagnosis and localhost rate-limit retry-denial diagnosis without launching a browser or mutating Project Sources.

Out of scope:

- No change to ChatGPT Project deletion freeze.
- No change to Project Source mutation behavior.
- No source-add timeout masking.
- No full-direct/full-localhost auto-green behavior.
- No artifact adoption/current mutation by this candidate.

## Validation performed in candidate build environment

- `bash -n chatgpt_claudecode_workflow_release_control.sh`
- `python3 -m py_compile tests/test_promptbranch_shell_scripts.py promptbranch_version.py`
- Fast fixture tests:
  - `tests/test_promptbranch_shell_scripts.py::test_release_control_all_tests_summary_diagnoses_source_add_readtimeout_by_transport`
  - `tests/test_promptbranch_shell_scripts.py::test_release_control_all_tests_summary_diagnoses_localhost_rate_limit_retry_denial`
- Existing focused classification tests:
  - `tests/test_promptbranch_shell_scripts.py::test_release_control_all_tests_summary_accepts_ok_false_verified_recovered_ask_live_payload`
  - `tests/test_promptbranch_shell_scripts.py::test_release_control_all_tests_summary_rejects_verified_recovered_ask_live_with_functional_failure`
  - `tests/test_promptbranch_shell_scripts.py::test_release_control_full_localhost_rate_limit_retry_is_denylisted_before_sleep`
- Version and control-surface tests.

## Operator validation still required

Install the candidate ZIP and run the full strict release gate:

```bash
timeout --foreground 10800 ./chatgpt_claudecode_workflow_release_control.sh \
  --install-from-zip "$zip" \
  --version "$ver" \
  --run-all-tests \
  --strict-source-kind-matrix \
  --adopt-after-validation \
  --skip-docker-logs \
  --prune-release-logs \
  --release-log-keep 12
```

The candidate is not accepted/current until `pb artifact current --json` confirms runtime, state artifact, state source, registry current, and consistency alignment.
