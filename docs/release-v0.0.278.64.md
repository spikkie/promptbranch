# Release v0.0.278.64

## Scope

Builds on v0.0.278.63.

This release preserves the successful local headed Patchright debug path from v0.0.278.63 and adds DOM-delta submit confirmation for cases where the UI clearly commits the current prompt but the backend/network marker observer does not capture a prompt-bearing submit request.

## Changes

- Preserve Patchright-only headed local debug behavior and safe Linux Chrome flags.
- Preserve trusted-paste fill and existing submit dispatch mechanics.
- Add bounded DOM-delta confirmation for plain prompts:
  - accept only when a new role-specific user turn count appears after the pre-submit baseline and the latest user text matches the current prompt;
  - or when the generic turn suffix shows the current prompt followed by a new assistant turn;
  - keep marker-based confirmation preferred when protocol markers are available.
- Let the normal answer wait/extraction continue after DOM-delta submit confirmation instead of failing early as `submit_causality_not_confirmed`.
- Keep stale-answer protection: plain prompt text alone is not enough without a count/order delta.

## Non-goals

- No fill-path change.
- No browser-launch change.
- No Playwright switch.
- No broad latest-answer fallback.
