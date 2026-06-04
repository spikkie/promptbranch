# Release v0.1.29 — structured full-test evidence summary

## Scope

`v0.1.29` adds structured full-test evidence summary generation to the repo-local release-control workflow.

When `chatgpt_claudecode_workflow_release_control.sh --run-tests` executes the full test/report block, it now writes:

```text
.pb_profile/release_logs/<version>/post_release_validation.<version>.summary.json
```

The summary captures:

- release version and artifact name;
- `pb test full` exit code;
- `pb test report` exit code;
- report status and failure count;
- full-test log path;
- report JSON path;
- session log path;
- service health JSON path when available;
- validation classification fields used by existing evidence readers.

## Intent

The previous `v0.1.28` evidence-status command could infer a green full-test run from release logs, but that remained medium-confidence evidence. This release makes future full-test evidence high-confidence by producing a machine-readable summary directly from the release-control test block.

## Non-goals

This release does not:

- adopt a candidate;
- upload a Project Source;
- change ZIP import behavior;
- change browser automation;
- run tests automatically from `evidence-status`;
- mutate baseline state from evidence inspection.

## Validation

Expected focused validation:

```bash
python3 -m py_compile promptbranch_cli.py
bash -n chatgpt_claudecode_workflow_release_control.sh
pytest -q tests/test_promptbranch_shell_scripts.py::test_release_control_tests_only_skips_release_mutation_steps \
  tests/test_promptbranch_cli.py::test_release_evidence_status_reports_green_post_release_summary \
  tests/test_promptbranch_cli.py::test_release_baseline_status_embeds_full_test_evidence
pb test smoke --json --path .
pb release docs-status --version v0.1.29 --json
pb release install --artifact ./chatgpt_claudecode_workflow-2_v0.1.29.zip --version v0.1.29 --target-version v0.1.29 --plan --json
```

## Operator usage

After installing `v0.1.29`, the next future full-test run should create structured evidence automatically:

```bash
./chatgpt_claudecode_workflow_release_control.sh \
  --version <version> \
  --install-from-zip ~/Downloads/chatgpt_claudecode_workflow-2_<version>.zip \
  --skip-source-add \
  --run-tests \
  --prune-release-logs \
  --release-log-keep 12

pb release evidence-status --version <version> --json
```

If the full-test report is green, `evidence-status` should report high-confidence structured evidence instead of log-inferred medium confidence.
