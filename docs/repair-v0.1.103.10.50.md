# Repair v0.1.103.10.50 — auth bootstrap backend-api 403 guardrail is terminal

This slice preserves the Docker-only browser path and the v0.1.103.10.40-v0.1.103.10.49 live-profile repairs. It tightens release-control auth/bootstrap validation so backend-api 403 guardrail telemetry is not accepted as a clean Cloudflare/auth-ready state just because the page still shows a composer.

## Change

- `scripts/pb-browser-cloudflare-validation.sh` now fails strict validation when the standard browser summary contains `backend_api_guardrail_seen=true` / backend-api 403 guardrail events.
- `chatgpt_claudecode_workflow_release_control.sh` now classifies backend-api 403 during auth bootstrap as `browser_backend_403_guardrail`, restarts only the candidate service to clear the held auth session, and stops before Project Source add or full validation.
- Full release validation also treats backend-api 403 guardrail evidence as terminal even if the command itself returned success.

## Non-goals

- No host-CDP/session-manager revival.
- No copied-profile trust.
- No automatic reset of all profiles.
- No private backend-api operational dependency added.
