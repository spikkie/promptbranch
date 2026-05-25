# Release v0.0.274

Base: `chatgpt_claudecode_workflow_v0.0.273.zip`

## Scope

Read-only MVP Definition of Done visibility/check only.

## Changes

- Add `pb artifact mvp-dod --json` as a read-only check for `docs/mvp-definition-of-done.md`.
- Surface the DoD check inside `pb artifact mvp-status --json` under `mvp_definition_of_done`.
- Add `commands.inspect_mvp_dod` to the MVP cockpit payload.
- Preserve the accepted `.gitignore` content and remove no additional runtime behavior.

## Non-goals

- No enforcement of the full MVP DoD gate.
- No artifact intake/adoption/source behavior changes.
- No lifecycle mutation changes.
- No Git behavior changes.

## Validation

- `python3 -m compileall -q .`
- `bash -n scripts/post-release-validation.sh scripts/finalize-artifact-intake-mvp.sh chatgpt_claudecode_workflow_release_control.sh`
- focused parser and MVP DoD tests
