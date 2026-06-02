# Release v0.1.12 — baseline-status UX clarification

## Base

Built from `chatgpt_claudecode_workflow-2_v0.1.11.zip`.

## Scope

Improve the read-only release-status UX so `pb release baseline-status` clearly communicates its intended context:

- `baseline-status` is a post-adoption verifier.
- It should be used after adoption to verify runtime/source/artifact alignment.
- It is not the right command for installed-but-not-adopted development candidates.
- Development candidates should use `pb release checkpoint --mode continue` or `pb release dev-status --json`.

## Changed surfaces

- `promptbranch_cli.py`
- `tests/test_promptbranch_cli.py`
- `tests/test_cli_parser.py`
- `docs/design/promptbranch-mvp-living-design.md`
- `docs/design/promptbranch-mvp-living-design.drawio`
- version surfaces

## Non-goals

- No install mutation logic.
- No Project Source mutation.
- No artifact adoption.
- No full test automation change.
- No Git mutation.

## Validation

Focused validation for this release should include:

```bash
python3 -m pytest -q tests/test_promptbranch_cli.py -k 'release_baseline_status or release_docs_status or release_checkpoint or release_dev_status or release_install_plan or release_lifecycle_plan or release_config or release_doctor'
python3 -m pytest -q tests/test_cli_parser.py -k 'release_baseline_status or release_docs_status or release_checkpoint or release_dev_status or release_install or release_lifecycle or release_config'
pb release docs-status --version v0.1.12 --json
pb release checkpoint --artifact ./chatgpt_claudecode_workflow-2_v0.1.12.zip --version v0.1.12 --target-version v0.1.12 --mode continue --json
pb test smoke --json
```
