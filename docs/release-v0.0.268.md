# Release v0.0.268

Finalizer lifecycle-status snapshot integration release from `chatgpt_claudecode_workflow_v0.0.267.zip`.

## Scope

- Integrate the read-only `pb release lifecycle-status --json` cockpit into `scripts/post-release-validation.sh`.
- Write a lifecycle-status snapshot under `.pb_profile/release_logs/<version>/pb_release_lifecycle_status.<version>.json`.
- Add lifecycle-status snapshot metadata to `post_release_validation.<version>.summary.json`.
- Include the lifecycle-status step in structured validation classification.
- Keep service health and Project Source probes skipped by default via the lifecycle-status command defaults.

## Non-goals

- No artifact intake semantic changes.
- No install/upload/adopt behavior changes.
- No Project Source mutation changes.
- No Git commit or push behavior changes.
- No write-capable lifecycle consolidation.

## Operator value

After finalization, the release log directory now contains the normal post-release validation summary plus a local-first lifecycle-status cockpit snapshot for the same version. This makes the accepted baseline, candidate state, finalizer state, and next safe action visible from one release-log bundle.
