# Release v0.0.278.71 — ask-live attachment result-detection repair

## Purpose

Repair the `pb test ask-live --json` attachment false negative observed in v0.0.278.70.

The v0.0.278.70 full ask-live run proved the visible UI could submit an attachment, navigate into a `/c/...` conversation, and render the expected attachment sentinel. The test still failed because the submit detector relied on network submit causality and returned before reading the rendered assistant answer.

## Scope

This is a narrow repair.

Changed:

- Add an attachment-only fallback for unconfirmed submit evidence.
- If attachment paths were supplied, the current URL is a conversation URL, and a fresh visible assistant answer is rendered, promote that answer as successful result evidence.
- Mark the submit evidence with `attachment_visible_answer_after_unconfirmed_submit`.
- Capture the current `/c/...` URL as the conversation URL in that fallback.
- Add regression coverage for attachment visible-answer promotion and for non-attachment fallback exclusion.

Not changed:

- Plain ask fill/submit behavior.
- Prompt-file fill/submit behavior.
- Temporary project creation/removal behavior.
- Attachment upload behavior.
- Network submit observer behavior.

## Operator validation

Run attachment-only first:

```bash
pb test ask-live --json \
  --profile-dir ./.pb_profile_local_debug \
  --only file_attachment,prompt_file_with_attachment \
  2>&1 | tee pb_test.ask_live.v0.0.278.71.attachments.log
```

Then run the full profile:

```bash
pb test ask-live --json \
  --profile-dir ./.pb_profile_local_debug \
  2>&1 | tee pb_test.ask_live.v0.0.278.71.full.log
```

## Expected evidence

Attachment steps should show:

```text
submit_confirmation_mode: attachment_visible_answer_after_unconfirmed_submit
contains_expected_sentinel: true
conversation_url: https://chatgpt.com/.../c/...
status: verified
```

## Validation

Local validation for this release should include:

- Python compile checks.
- Focused response-completion regression tests.
- Focused ask-live parser/CLI tests.
- ZIP hygiene and root-layout verification.
