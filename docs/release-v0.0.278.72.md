# Release v0.0.278.72 — ask-live file-attachment submit readiness repair

## Scope

Narrow repair on top of v0.0.278.71 for the remaining `pb test ask-live --only file_attachment` false failure.

The v0.0.278.71 attachment-only run proved `prompt_file_with_attachment` could be recovered by visible-answer fallback, but `file_attachment` still failed before any `/c/...` conversation URL was captured. The failure path used primary keyboard Enter immediately after upload readiness evidence was too weak.

## Changes

- Add an attachment submit-readiness wait after browser file input upload.
- Require the composer send button to become visible/enabled before attachment submit dispatch.
- Prefer the visible enabled send button for attachment asks instead of primary Enter dispatch.
- Preserve the v0.0.278.71 visible-answer fallback for attachment submits whose network causality is missed.
- Prevent ask-live from reporting `contains_expected_sentinel: true` when the response is an internal failed-result dictionary instead of a real assistant answer.

## Non-goals

- No change to plain ask fill/submit behavior.
- No change to prompt-file-only fill/submit behavior.
- No change to temporary project creation/removal.
- No change to attachment upload mechanics.

## Suggested validation

```bash
pb test ask-live --json \
  --profile-dir ./.pb_profile_local_debug \
  --only file_attachment,prompt_file_with_attachment \
  2>&1 | tee pb_test.ask_live.v0.0.278.72.attachments.log
```

Expected evidence for attachment steps:

```text
contains_expected_sentinel: true
conversation_url: .../c/...
submit_confirmed: true
submit_confirmation_mode: clicked_submit_button or attachment_visible_answer_after_unconfirmed_submit
```

## Validation performed during packaging

- Python compile check.
- Focused pytest for response completion and CLI ask-live behavior.
- Reopened ZIP and verified root layout/hygiene.
