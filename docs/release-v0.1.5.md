# Release v0.1.5 — Read-only development-head status

## Base

Development continues monotonically from `chatgpt_claudecode_workflow-2_v0.1.4.zip`.
The currently adopted baseline may still be older during focused-test development.

## Scope

Adds a read-only development status command:

```bash
pb release dev-status --json
```

The command separates:

- accepted/adopted baseline from `pb artifact current`
- installed runtime code version
- local development candidate ZIPs for the configured artifact line
- selected development head
- expected next normal version from the accepted baseline
- next monotonic development version from the development head

## Safety boundary

`pb release dev-status` is diagnostic only.
It does not download artifacts, migrate candidates, install files, run tests, add Project Sources, adopt artifacts, update state, commit, or push Git changes.

## Motivation

During CI-style development, runtime code and local candidate ZIPs may intentionally advance beyond the adopted baseline while focused tests are run.  This command makes that state explicit so operators can continue monotonically without rewriting earlier development versions and run full release-control only at the adoption checkpoint.

## Validation

Focused validation used for this release:

```bash
python3 -m pytest -q tests/test_promptbranch_cli.py -k 'release_dev_status or release_install_plan or release_lifecycle_plan or release_config or release_doctor'
python3 -m pytest -q tests/test_cli_parser.py -k 'release_dev_status or release_install or release_lifecycle or release_config'
python3 scripts/orchestration/validate_examples.py
python3 -m pytest -q tests/orchestration/test_orchestration_examples.py
python3 -m compileall -q .
```
