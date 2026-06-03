# Release v0.1.25 — Threshold-version projection clarification

Base: `chatgpt_claudecode_workflow-2_v0.1.24.zip`

## Scope

Clarify the read-only full-test/adoption threshold projection before the threshold becomes operationally important.

## Changes

- Fix `expected_threshold_version` in `pb release status-guide --json` so pre-threshold guidance reports the projected threshold candidate instead of always reporting the immediate next development candidate.
- Add explicit `versions_until_expected_threshold` and `calculation_rule` fields to the threshold notice payload.
- Keep `next_release_reaches_full_test_threshold` true only when the next focused-development release actually reaches the threshold.
- Update the living design Markdown and editable draw.io source to document the corrected threshold projection semantics.

## Non-goals

- No full-test/adoption checkpoint.
- No Project Source upload.
- No artifact adoption.
- No Git mutation.

## Validation

- `python3 -m compileall -q .`
- focused release status-guide/checkpoint/countdown tests
- `pb test smoke --json --path .`
- `pb release docs-status --version v0.1.25 --json`
- `pb release config --json`
- `pb release install --artifact ... --plan --json`
- `pb release lifecycle --artifact ... --plan --json`
- ZIP hygiene/root-layout verification
