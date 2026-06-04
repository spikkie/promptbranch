# Release v0.1.28 — read-only full-test evidence/status

## Scope

This release is a focused read-only lifecycle evidence slice built from `chatgpt_claudecode_workflow-2_v0.1.27.zip`. It adds full-test evidence/status reporting without changing ask/reply runtime behavior, source mutation, artifact adoption, ZIP import, or browser automation.

## Changes

- Add `pb release evidence-status` as a read-only full-test evidence verifier.
- Inspect local structured post-release validation summaries under `.pb_profile/release_logs/`.
- Fall back to conservative release-log inference when structured evidence is not available.
- Embed `full_test_evidence` in `pb release baseline-status --json`.
- Add evidence-status command guidance to release status-guide output.
- Update the living design document and editable draw.io source for the evidence/status slice.

## Non-goals

- No full-test execution from the new evidence command.
- No adoption.
- No Project Source upload.
- No ZIP import behavior change.
- No browser automation or ask/reply runtime change.

## Validation

Expected focused validation for this slice:

```bash
python3 -m compileall -q .
pytest -q tests/test_promptbranch_cli.py -k 'release_evidence_status or release_baseline_status or release_status_guide or release_checkpoint or promptbranch_smoke_step_specs'
pb test smoke --json --path .
pb release docs-status --version v0.1.28 --json
pb release config --json
pb release install --artifact ./chatgpt_claudecode_workflow-2_v0.1.28.zip --version v0.1.28 --target-version v0.1.28 --plan --json
pb release lifecycle --artifact ./chatgpt_claudecode_workflow-2_v0.1.28.zip --version v0.1.28 --target-version v0.1.28 --plan --json
```
