# Release v0.1.32

## Scope

Clean up stale `next_normal_*` guidance in development-candidate release status output.

## Changes

- Suppress `next_normal_status_guide`, `next_normal_checkpoint`, `next_normal_version`, and `next_normal_artifact` in `pb release status-guide --json` when the detected context is `development_candidate`.
- Add `next_normal_guidance_applicable` and `suppressed_next_normal_guidance` so automation can distinguish intentionally suppressed normal-baseline guidance from missing data.
- Keep `next_development_*` guidance as the active handoff for focused development candidates.
- Preserve the post-adoption baseline path, where `next_normal_*` guidance remains correct and visible.

## Validation

- Focused status-guide tests cover both development-candidate suppression and post-adoption next-normal guidance.
- Smoke remains the required cheap runtime check after install.

## Non-goals

- No adoption changes.
- No Project Source upload changes.
- No full-test execution changes.
- No browser automation changes.
