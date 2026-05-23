# Release v0.0.259

## Scope

This release fixes artifact-intake state recovery for the real release-candidate path.

It keeps the strict real-candidate gate unchanged, but allows the operator to continue when `pb ask-release` times out at the service-client layer after ChatGPT later writes a valid release-candidate reply into the transcript.

## Changes

- `pb task answer parse --latest --json` now promotes a valid parsed protocol reply into `.pb_profile/ask_protocol_runs/` when it can be matched to an existing request id.
- `pb artifact intake --from-last-answer` can recover from the live latest parsed task answer when the latest persisted protocol-run record is stale, failed, or a previous no-artifact smoke.
- `--local-file` / `--manual-import-file` manual import can proceed when exactly one valid ZIP candidate exists in the recovered parsed latest answer.
- The strict `--require-real-candidate` gate is preserved and still fails closed when no real candidate exists.

## Validation

- `python3 -m compileall -q .`
- `pytest -q tests/test_cli_parser.py tests/test_promptbranch_cli.py`
- ZIP layout and hygiene verification after packaging.

## Non-goals

- No automatic browser-context download for `sandbox:` artifacts.
- No Project Source mutation.
- No local adoption.
- No Git commit or push.
