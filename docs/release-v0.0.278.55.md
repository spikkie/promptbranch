# Release v0.0.278.55

## Scope

Route primary keyboard Enter prepare-only fast-fail into the retry trusted-refill path, then dispatch the retry with the visible enabled send button click introduced in v0.0.278.54.

## Intent

v0.0.278.54 added the retry send-button-click dispatch, but the live v0.0.278.54 diagnostic stopped after the primary Enter prepare-only fast-fail and never exercised the retry branch. This release repairs that control-flow gap.

## Changes

- Preserve primary raw Enter as the first submit attempt.
- Preserve trusted refill behavior and leave `_fill_chat_prompt` unchanged.
- Classify `submit_prepare_without_message_commit` / `submit_prepare_only_timeout` as retryable.
- Record `submit_keyboard_enter_retry_reason = primary_prepare_only_fast_fail` when this route is taken.
- Keep `/backend-api/f/conversation/prepare` excluded from submit confirmation.
- Continue requiring exact marker/sentinel causality for success.

## Validation

- compileall
- focused pytest for submit retry routing and send-button-click retry behavior
- ZIP hygiene verification
