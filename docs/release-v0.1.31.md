# Release v0.1.31 — strict `--skip-source-add` preservation

## Purpose

`v0.1.31` fixes a release-control guardrail issue observed after installing `v0.1.30`: a run that included `--skip-source-add` still reached the Project Source add path during candidate ZIP install.

The flag is intended to make Project Source mutation impossible for focused local install/checkpoint/smoke runs. This release makes that behavior explicit and regression-tested.

## Scope

This release keeps the behavior control-plane focused. It changes only release-control source-add gating and test coverage around the delegated candidate workflow.

## Behavior

`chatgpt_claudecode_workflow_release_control.sh` now preserves skip-source-add intent across Stage-0 candidate delegation by exporting `PROMPTBRANCH_RELEASE_SKIP_SOURCE_ADD=1` when the original operator arguments include `--skip-source-add`.

The final Project Source add block now requires both:

```text
skip_source_add == 0
PROMPTBRANCH_RELEASE_SKIP_SOURCE_ADD != 1
```

If either guard disables source add, the script prints:

```text
Source add skipped: --skip-source-add
```

This makes focused install logs auditable and prevents accidental `promptbranch src add` / Project Source mutation when the operator requested a local-only candidate install.

## Regression coverage

Added a shell-script regression test that exercises the actual Stage-0 candidate delegation path:

```text
outer release-control script
  -> extracts candidate chatgpt_claudecode_workflow_release_control.sh
  -> execs delegated candidate script
  -> imports candidate ZIP
  -> packages candidate
  -> proves promptbranch src add was not invoked
```

The existing automatic ZIP import test also asserts that `--skip-source-add` prints the skip marker and does not call `promptbranch src add`.

## Non-goals

This release does not change:

- adoption semantics
- full-test execution
- artifact verification rules
- Project Source add behavior when `--skip-source-add` is absent
- browser automation
- runtime service startup

## Validation target

Focused validation should include:

```text
bash -n chatgpt_claudecode_workflow_release_control.sh
python3 -m compileall -q .
python3 -m pytest -q tests/test_promptbranch_shell_scripts.py::test_release_control_stage0_delegation_preserves_skip_source_add
python3 -m pytest -q tests/test_promptbranch_shell_scripts.py::test_release_control_automatically_imports_candidate_zip_without_bcompare
pb test smoke --json --path .
pb release docs-status --version v0.1.31 --json
pb release install --artifact ./chatgpt_claudecode_workflow-2_v0.1.31.zip --version v0.1.31 --target-version v0.1.31 --plan --json
pb release lifecycle --artifact ./chatgpt_claudecode_workflow-2_v0.1.31.zip --version v0.1.31 --target-version v0.1.31 --plan --json
```
