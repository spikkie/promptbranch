# v0.1.103.10.59 — run release-live-continuous through Docker service, not local Patchright

## Scope

- Keep all-in-Docker only.
- Route `pb test release-live-continuous` through the Docker service transport.
- Map the explicit release-live slot to `/app/profile` before live preflight and continuous validation.
- Keep the warmup `/g/.../c/...` URL and continuous browser-session design.
- Do not revive host-CDP/session-manager.
- Do not reintroduce copied-profile trust.

## Expected behavior

`live_profile_preflight` and `release-live-continuous` now use the same Docker browser envelope rather than mixing Docker service preflight with local host Patchright execution.
