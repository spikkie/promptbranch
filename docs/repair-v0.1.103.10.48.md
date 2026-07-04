# Repair v0.1.103.10.48 — backend-api 403 guardrail classification across release validation

## Scope

- Keep all-in-Docker only.
- Do not revive host-CDP/session-manager.
- Preserve explicit Docker live profile bootstrap and `.pb_profile_local_debug_pools` import preservation.
- Keep live validation on `/c/...` conversation URLs.
- Keep `docker_live_profile_challenged` terminal for release-live ask/live cascades.
- Treat observed ChatGPT `/backend-api/...` 403 responses as diagnostic browser guardrail evidence only.
- Do not treat private ChatGPT web-app endpoints as an operational API contract.

## Behavior

When release validation observes backend-api 403 guardrail evidence, browser automation now fails fast with a structured challenge status instead of waiting for a generic service/browser timeout or persisting conversation-history cooldown state.

Profile-specific challenge statuses:

- `.pb_profile_local_debug_pools/.../release-live/slots/...` → `docker_live_profile_challenged`
- standard Docker profile paths such as `.pb_profile/browser/default` or `/app/profile` → `docker_standard_profile_challenged`
- other browser/profile contexts → `browser_backend_403_guardrail`

Release-control now enables fail-fast challenge detection for full validation, localhost service validation, live profile preflight, project selection, and release-live browser steps. If full validation already saw a backend-api 403 guardrail, remaining live browser steps are skipped as `skipped_browser_backend_403_guardrail`; import smoke and artifact guard still run.

## Out of scope

- No Cloudflare bypass.
- No direct reliance on ChatGPT private backend-api endpoints as operational API calls.
- No host-CDP/session-manager.
- No copied-profile trust.
- No Project Source mutation behavior change.
