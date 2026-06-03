# Release v0.1.24 — Pre-threshold full-test countdown visibility

Base: `chatgpt_claudecode_workflow-2_v0.1.23.zip`

## Scope

Make the focused-development full-test/adoption threshold countdown explicit before the threshold is reached.

## Changes

- Add a read-only `full_test_countdown` payload for release drift complexity.
- Expose countdown fields in `pb release status-guide --json` and plain-text output.
- Expose countdown fields in `pb release checkpoint --mode continue --json` and plain-text output.
- Add smoke contract coverage for the plain-text `full_test_countdown_active=` marker.
- Add focused tests for near-threshold and threshold-now countdown behavior.

## Non-goals

- No adoption.
- No full release-control execution.
- No Project Source upload.
- No accepted baseline change.
- No write-capable lifecycle behavior.

## Validation

- `python3 -m compileall -q .`
- focused release status-guide/checkpoint/countdown/smoke tests
- `pb test smoke --json --path .`
- read-only release plan commands
- ZIP hygiene and root-layout verification
