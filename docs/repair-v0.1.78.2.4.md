# Repair v0.1.78.2.4 — Delete-frozen live-test profile alignment

## Problem

After ChatGPT Project deletion was frozen, the live test profiles still described and defaulted toward temporary project creation/removal. Operators also had to run the full validation stack manually across many commands.

## Change

- `pb test ask-live` defaults to the retained project `itest-promptbranch-retained-delete-frozen`.
- `pb test visual-artifact-roundtrip` defaults to the same retained project.
- `pb test release-live` defaults to the same retained project.
- The live profiles force keep-project semantics while project deletion is frozen.
- Operator/help text no longer claims automatic temporary project deletion.
- `chatgpt_claudecode_workflow_release_control.sh --run-all-tests` runs the full operator validation stack in one command:
  - `pb test full` over direct and localhost transports
  - `pb test ask-live`
  - `pb test visual-artifact-roundtrip`
  - `pb test release-live`
  - `pb test import-smoke`
  - `pb artifact guard`
- The all-tests runner continues after individual failures and writes `pb_test.all.<version>.summary.json` with final `GO` or `FIX`.

## Safety boundary

No ChatGPT Project deletion is re-enabled. Existing leaked `itest-promptbranch-*` projects are not deleted.

## Validation target

Focused tests must prove live profile defaults, no remove-project calls, all-tests shell orchestration, version metadata, project control surface, compileability, shell syntax, and Artifact Guardian compliance.
