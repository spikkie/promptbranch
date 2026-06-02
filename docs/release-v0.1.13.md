# Release v0.1.13 — baseline-status development-context UX hardening

## Base

Built from accepted/development baseline:

```text
chatgpt_claudecode_workflow-2_v0.1.12.zip
```

## Scope

This is a focused release-status UX slice. It keeps `pb release baseline-status` read-only and post-adoption-only, but makes development-candidate misuse easier to diagnose.

## Changes

- Added `release_status_context` to `pb release baseline-status --json`.
- Explicitly reports whether `baseline-status` is applicable in the detected context.
- For installed-but-not-adopted development candidates, reports the primary read-only command to run instead:

```bash
pb release checkpoint --artifact ./<candidate>.zip --version <version> --target-version <version> --mode continue --json
```

- Adds a warning code when `baseline-status` is being used against a development candidate:

```text
release_baseline_status_post_adoption_only_context
```

- Non-JSON output now includes:

```text
baseline_status_applicable=<true|false>
primary_read_command=<command>
```

## Non-goals

- No install/source/adopt mutation.
- No Project Source upload.
- No Git mutation.
- No full browser/service suite in this focused build.

## Validation

```bash
python3 -m pytest -q tests/test_promptbranch_cli.py -k 'release_baseline_status or release_docs_status or release_checkpoint or release_dev_status or release_install_plan or release_lifecycle_plan or release_config or release_doctor'
python3 -m pytest -q tests/test_cli_parser.py -k 'release_baseline_status or release_docs_status or release_checkpoint or release_dev_status or release_install or release_lifecycle or release_config'
python3 scripts/orchestration/validate_examples.py
python3 -m pytest -q tests/orchestration/test_orchestration_examples.py
python3 -m compileall -q .
pb release docs-status --version v0.1.13 --repo-path . --json
pb release checkpoint --artifact ./chatgpt_claudecode_workflow-2_v0.1.13.zip --version v0.1.13 --target-version v0.1.13 --mode continue --json
```
