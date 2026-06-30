# v0.1.103.2 — Docker browser parity passive-auth and profile-bootstrap repair

## Baseline

`v0.1.103.2` is built on top of diagnostic candidate `v0.1.103.1`, which itself was built from `chatgpt_claudecode_workflow-2_v0.1.103.zip` for Docker browser parity investigation.

## Purpose

Repair the first Docker browser parity diagnostic so it measures the actual next blocker. The `v0.1.103.1` live run proved the service process was running under Xvfb with the Promptbranch Docker browser envelope, but the script called a missing `/v1/auth-readiness` endpoint and the manual `/v1/login-check` path clicked the login button, reached `/api/auth/error`, then waited for a hidden 600-second manual-login flow inside Xvfb.

## Changes

- Add `POST /v1/auth-readiness` as a passive, Promptbranch-native compatibility endpoint.
- Add `run_passive_auth_readiness` through the service and browser client layers.
- Passive auth readiness navigates to ChatGPT, waits only for normal challenge settling, and reports state without clicking the login button.
- Report `title`, `current_url`, `challenge_detected`, `auth_visible`, `login_visible`, `signup_visible`, `anonymous_visible`, `composer_visible`, `project_page_visible`, `logged_in`, and `session_state_reason`.
- Repair `scripts/docker-browser-parity-auth-readiness.sh` to fail its top-level result when passive auth readiness is not ready.
- Add `scripts/docker-browser-profile-bootstrap-host-chrome.sh` to seed `.pb_profile_docker` with normal host Chrome; Docker mounts that profile as `/app/profile`.

## Explicit non-goals

- No Cloudflare bypass.
- No automated challenge solving.
- No Project Source mutation.
- No artifact adoption/current mutation.
- No hidden manual-login wait in the diagnostic path.
- No source-app-specific profile or script naming.

## Expected diagnostic outcomes

An unauthenticated but non-challenged Docker profile should return `ok=false`, `status=auth_profile_not_logged_in`, and `release_blocking=true` quickly. A seeded and trusted Docker profile should return `ok=true`, `status=auth_preflight_ready`, `logged_in=true`, `challenge_detected=false`, and `composer_visible=true`.
