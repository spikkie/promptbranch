# Release v0.1.91 — Run-all evidence reuse proof and localhost matrix cooldown audit

## Baseline

Accepted/current baseline:

```text
chatgpt_claudecode_workflow-2_v0.1.90.1.zip
```

## Purpose

`v0.1.91` makes the `--run-all-tests` validation path easier to trust after a successful `--run-tests` gate. It proves and reports that already-passed direct full-test evidence is reused only when artifact hash and validation dimensions match, while localhost validation remains a separate executed matrix step with explicit cooldown/retry audit evidence.

## Scope

- Reuse `full_direct` evidence in `--run-all-tests` only when the existing validation evidence matches artifact SHA256, version, artifact ref, transport, service base, runtime mode, strict source-kind matrix mode, command signature, and green test/report exit codes.
- Add an explicit `localhost_matrix_cooldown_audit` section to the all-tests summary.
- Make reused full-test summaries expose top-level `release_validation_groups` so duplicate local groups can be skipped in later transports only after proven direct evidence.
- Keep localhost/offline cooldown retry fail-closed: these groups must not sleep/retry on browser cooldown evidence.

## Out of scope

- No Project Source mutation behavior changes.
- No artifact adoption/current behavior changes.
- No ChatGPT Project deletion behavior changes.
- No loop behavior changes.
- No deployment or Kubernetes behavior.
- No live browser selector/path changes.

## Validation performed in candidate environment

```bash
python3 -m pytest -q \
  tests/test_promptbranch_shell_scripts.py::test_release_control_run_all_reuses_prior_run_tests_direct_evidence_and_audits_localhost \
  tests/test_promptbranch_shell_scripts.py::test_release_control_all_tests_summary_reports_localhost_cooldown_audit_contract \
  tests/test_promptbranch_shell_scripts.py::test_release_control_declares_validation_evidence_reuse_fail_closed_contract \
  tests/test_promptbranch_shell_scripts.py::test_release_control_all_tests_summary_reports_validation_reuse_groups
```

Result:

```text
4 passed
```

Full candidate validation also included focused shell regression tests, version tests, project-control tests, loop regressions, compileall, shell syntax, Artifact Guardian, artifact verify, and ZIP hygiene.

## Expected operator proof

After `v0.1.91 --run-tests --adopt-after-validation` succeeds, run:

```bash
zip=~/Downloads/chatgpt_claudecode_workflow-2_v0.1.91.zip
ver=v0.1.91

timeout --foreground 10800 ./chatgpt_claudecode_workflow_release_control.sh \
  --install-from-zip "$zip" \
  --version "$ver" \
  --run-all-tests \
  --strict-source-kind-matrix \
  --adopt-after-validation \
  --skip-docker-logs \
  --prune-release-logs \
  --release-log-keep 12 \
  2>&1 | tee ~/tmp/release_control.$ver.run_all_tests.adopt.log
```

The all-tests summary should show:

```text
validation_reuse.reused_groups includes full_direct
validation_reuse.executed_groups includes full_localhost
localhost_matrix_cooldown_audit.status is clear or review with explicit evidence
```
