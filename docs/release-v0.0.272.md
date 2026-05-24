# Release v0.0.272 — Human summary regression guard

## Scope

Build from accepted `chatgpt_claudecode_workflow_v0.0.271.zip`.

This release adds a display-only regression guard for the finalizer lifecycle human summary.

## Changes

- Add `release_lifecycle_human_summary_guard` validation output under `.pb_profile/release_logs/<version>/`.
- Classify guard failures as `human_summary_regression_failure`.
- Include `lifecycle_human_summary_guard` and `lifecycle_human_summary_guard_path` in the post-release validation summary.
- Print the human-summary guard status in the terminal human summary.

## Non-goals

- No lifecycle-status JSON contract changes.
- No artifact-intake behavior changes.
- No install, source upload, adoption, policy-sync, or Git behavior changes.

## Validation intent

The finalizer should fail if key lifecycle fields are present in the raw lifecycle-status snapshot but the human-summary extraction path would hide them as `unknown`.
