# v0.1.103.10.49 — run all release-live setup and ask steps in the same explicit live slot profile

## Scope

- Keep all-in-Docker only.
- Keep explicit release-live slot profile state and challenge fail-fast handling.
- Use `.pb_profile_local_debug_pools/release-live/slots/slot-1` for the complete release-live setup/execution flow.
- Keep `.pb_profile_local_debug` optional and non-acting for release-live.
- Make Docker bootstrap/image defaults derive from the release VERSION/PROMPTBRANCH_VERSION when `PROMPTBRANCH_SERVICE_IMAGE_TAG` is unset.
- Do not revive host-CDP/session-manager.
- Do not reintroduce copied-profile trust.

## Validation

Focused shell/static and package checks validate the same-slot release-live command topology, Docker image fallback, syntax, import-plan, and version coherence.
