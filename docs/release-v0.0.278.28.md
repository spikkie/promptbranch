# Release v0.0.278.29

Diagnostic release built from `chatgpt_claudecode_workflow_v0.0.278.27.zip`.

## Scope

- Track all prepare `conduit_token` values as a redacted token set.
- Preserve first/latest/all token fingerprints, counts, and active token policy in submit evidence.
- Capture post-prepare request/response resource types and initiator summaries.
- Classify `stream_started_without_user_message_commit` when stream status reports `IS_STREAMING` after prepare but no user-message backend commit is proven.

## Safety

Raw conduit tokens remain private in memory only. Structured output exposes only sha256_12 fingerprints, counts, booleans, and request metadata. Stale-answer guards remain fail-closed.

## Validation

Focused tests added for all-token fingerprint tracking, request resource/initiator capture, and stream-without-commit classification.
