# Release v0.1.11 — Read-only post-adoption baseline-status verifier

## Base

Built from the accepted baseline:

```text
chatgpt_claudecode_workflow-2_v0.1.10.zip
```

## Scope

Adds a narrow read-only release command:

```bash
pb release baseline-status --json
```

The command verifies post-adoption alignment between:

- running Promptbranch runtime version;
- adopted artifact version;
- adopted Project Source version;
- artifact registry current version;
- artifact-current consistency flags;
- optional explicit accepted ZIP verification;
- optional living-design docs validation.

## Non-goals

This release does not:

- install artifacts;
- upload Project Sources;
- run browser/full tests;
- adopt artifacts;
- update registry state;
- sync policy;
- commit or push Git state.

## Rationale

After a full-test/adoption checkpoint, development should restart from a clearly verified baseline. `baseline-status` gives the operator a cheap read-only command to prove the accepted baseline is aligned before opening the next monotonic development slice.

## Validation

Focused validation for this slice should include:

```bash
python3 -m pytest -q tests/test_promptbranch_cli.py -k 'release_baseline_status or release_docs_status or release_checkpoint or release_dev_status or release_install_plan or release_lifecycle_plan or release_config or release_doctor'
python3 -m pytest -q tests/test_cli_parser.py -k 'release_baseline_status or release_docs_status or release_checkpoint or release_dev_status or release_install or release_lifecycle or release_config'
pb release baseline-status --version v0.1.11 --artifact ./chatgpt_claudecode_workflow-2_v0.1.11.zip --include-docs --json
```
