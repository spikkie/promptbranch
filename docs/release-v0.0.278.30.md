# Release v0.0.278.30

Base artifact: `chatgpt_claudecode_workflow_v0.0.278.29.zip`
Target artifact: `chatgpt_claudecode_workflow_v0.0.278.30.zip`

## Purpose

Promote the `.29` diagnostic finding into the normal submit path: trusted keyboard Enter now performs the primary ChatGPT submit dispatch because button click can enter a prepare-only idle path.

## Changes

- Added `CHATGPT_KEYBOARD_ENTER_PRIMARY_SUBMIT` with default enabled behavior.
- Made keyboard Enter the primary `pb ask` submit dispatch.
- Kept button-click probing/fallback available when `CHATGPT_KEYBOARD_ENTER_PRIMARY_SUBMIT=0` for controlled diagnostics.
- Preserved stale-answer fail-closed behavior: a submit dispatch alone is not enough for a successful ask result.
- Added submit evidence fields for keyboard-primary operation:
  - `submit_keyboard_enter_primary_used`
  - `submit_keyboard_enter_status`
  - `submit_keyboard_enter_submit_confirmed`
  - `submit_keyboard_enter_backend_commit_confirmed`
  - `submit_keyboard_enter_fresh_answer_gate_required`
  - `submit_keyboard_enter_classification`
- Kept prepare-only classifications for regression detection.

## Safety boundary

This release does not accept stale answers and does not treat button-click prepare-only evidence as success. Final ask success still depends on the existing causal submit confirmation and response freshness guard.

## Validation

- Python compile check over repository Python files.
- Focused submit/browser client tests.
- Focused version/container/compose/CLI tests.
- ZIP reopened and checked for wrapper-folder and hygiene violations.
