# Repair note — v0.1.78.2.20.1

## Scope

- Base release: `v0.1.78.2.20`
- Repair version: `v0.1.78.2.20.1`
- Repair type: release-control flag repair
- Normal slice advanced: no

## Reason

The `v0.1.78.2.20` focused prompt-file smoke passed, but the recommended full release-control command used `--adopt-after-validation`, while `chatgpt_claudecode_workflow_release_control.sh` did not yet implement that option.

## Files changed

- `chatgpt_claudecode_workflow_release_control.sh`
- `tests/test_promptbranch_shell_scripts.py`
- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `tests/test_promptbranch_version.py`
- `docs/project/definition-of-done.md`
- `docs/project/release-status.md`
- `docs/project/status.md`
- `docs/project/decisions.md`
- `docs/project/migration.md`
- `docs/repair-v0.1.78.2.20.1.md`

## Behavior

`--adopt-after-validation` is now accepted only for the full release workflow with `--run-tests` or `--run-all-tests`. It refuses to run with `--skip-tests`, `--tests-only`, `--adopt-current`, `--adopt-if-green`, `--import-plan`, or the developer-only `--run-failing-tests` path. When validation exits green and the report/all-tests summary is green, release-control calls the existing verified `adopt_current_artifact` path.

## Validation performed

- Bash syntax check for `chatgpt_claudecode_workflow_release_control.sh`.
- Python compile check for changed Python/version files.
- Focused pytest for release-control shell-script adoption behavior and version consistency.
- Project control-surface tests.
- ZIP integrity and hygiene checks.

## Validation not performed

- Full release-control was not run in this environment.
- Live ChatGPT tests were not run in this environment.
- Artifact adoption/current verification was not run in this environment.

## Out of scope

- No prompt-file submit behavior changes.
- No CV generator changes.
- No Project Source add/remove behavior changes.
- No artifact registry redesign.
- No normal release slice advancement.
