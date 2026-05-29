# Release v0.0.278.59

## Scope

Build from `chatgpt_claudecode_workflow_v0.0.278.48.zip`.

This release preserves the verified-good `.48` prompt fill, trusted keyboard Enter submit path, submit confirmation, and response extraction behavior.

## Change

Adds a minimal pre-submit stale task detector for reused project conversations.

If the selected target is a project conversation URL and the active DOM has zero user turns, zero assistant turns, and zero generic conversation-turn nodes, Promptbranch treats the conversation surface as stale/prepare-only-risk and navigates back to the project home before asking. The normal `.48` one-shot ask path then runs from the project home so ChatGPT can create a fresh task.

## Non-goals

- No refill retry.
- No retry Enter loop.
- No send-button fallback experiment.
- No prepare/conduit archaeology as a default recovery path.
- No changes to CLI ask option semantics.

## Operator evidence

The ask result exposes:

- `ask_phase_timings.stale_task_surface_detection`
- `ask_phase_timings.fresh_task_fallback_used`
- `ask_phase_timings.fresh_task_fallback_reason`
- `ask_phase_timings.fresh_task_fallback_target_url`

## Validation intent

The intended live proof is:

1. Hydrated conversations continue through the `.48` path.
2. Empty/stale project conversations are moved to project home before submit.
3. Submit evidence still shows `submit_method=keyboard_enter` and `submit_confirmation_mode=network_submit_request` on successful runs.
