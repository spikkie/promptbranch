# Repair v0.1.103.7 — Docker parity Cloudflare challenge settle loop

`v0.1.103.7` narrows the Docker parity investigation to Cloudflare challenge settling.

## Scope

- Add `scripts/docker-browser-parity-cloudflare-check.sh`.
- Start or reuse the Docker parity service.
- Require `/v1/docker/browser-runtime` to report `docker_browser_parity_mode=true` and `profile_dir=/app/profile`.
- Open one keep-open browser session through `/v1/auth-readiness`.
- Poll `/v1/auth-readiness/session/status` for the same held session.
- Export bounded `auth_readiness_auth_challenge_detected_*` evidence through the existing safe exporter.

## Explicitly out of scope

- Project Source mutation.
- `/v1/login-check`.
- Login button clicks.
- Google auth flow.
- Browser architecture changes such as VNC/noVNC/xpra.
- Artifact adoption/current mutation.

## Operator command

```bash
PROMPTBRANCH_DOCKER_BROWSER_PROFILE=docker-browser-parity \
PROMPTBRANCH_AUTH_READINESS_KEEP_OPEN_SECONDS=300 \
./scripts/docker-browser-parity-cloudflare-check.sh
```
