# Release v0.1.2 — read-only release doctor artifact hardening

Base release: `chatgpt_claudecode_workflow-2_v0.1.1.1.zip`
Release version: `v0.1.2`
Release type: normal

## Scope

This release hardens the read-only lifecycle diagnostics around:

- `pb release doctor --artifact ZIP --version VERSION --json`
- artifact identity prefix reporting for worktree artifact lines such as `chatgpt_claudecode_workflow-2`
- candidate ZIP version/layout/hygiene reporting
- artifact/runtime/requested/target/adopted/source consistency checks
- lifecycle phase detail for candidate, source-uploaded, adopted-current, ready, and blocked states

## Changes

- Added explicit artifact prefix extraction from `<prefix>_<version>.zip` filenames.
- `pb release doctor --artifact` now reports `artifact_prefix`, `artifact_identity`, and `artifact_line`.
- Artifact inspection now exposes layout checks for wrapper-folder absence, VERSION validity, unsafe entries, hygiene violations, and nested ZIPs.
- Artifact consistency now reports requested-version and target-version match checks.
- Lifecycle phase detail now includes artifact filename, artifact prefix, and adopted-match status.
- Added regression coverage for `chatgpt_claudecode_workflow-2_vX.zip` artifact prefix preservation.

## Non-goals

This release does not add install, source upload, adoption, registry mutation, state mutation, Git commit, or Git push behavior to `pb release doctor`.

## Validation

Expected focused validation:

```bash
bash -n chatgpt_claudecode_workflow_release_control.sh
python3 scripts/orchestration/validate_examples.py
python3 -m pytest -q tests/test_promptbranch_cli.py -k 'release_doctor'
python3 -m pytest -q tests/orchestration/test_orchestration_examples.py
python3 -m compileall -q .
```
