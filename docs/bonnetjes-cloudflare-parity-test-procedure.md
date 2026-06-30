# Bonnetjes Cloudflare parity test procedure

This procedure is the supported diagnostic path for the Docker browser auth phase in `v0.1.103.9`.

## Goal

Prove that a clean, user-owned Chrome profile can clear the ChatGPT Cloudflare challenge and remain authenticated when bind-mounted into the Docker service as `/app/profile`.

## In scope

- Xvfb service display.
- Headed Patchright Chrome.
- `PROMPTBRANCH_DOCKER_BROWSER_PROFILE=bonnetjes-cloudflare-parity`.
- `PROMPTBRANCH_PROFILE_DIR=/app/profile`.
- `CHATGPT_DISABLE_FEDCM=1`.
- `CHATGPT_FILTER_NO_SANDBOX=0`.
- `CHATGPT_PATCHRIGHT_HEADED_SAFE_ARGS=0`.
- `CHATGPT_CONVERSATION_HISTORY_REQUEST_SHIELD_MODE=disabled`.
- Same-session Cloudflare settle polling.

## Out of scope

- Project Source mutation.
- `/v1/project-sources`.
- `/v1/login-check`.
- Automated Google login.
- Challenge bypass/defeat logic.
- Wholesale `docker cp /app/debug_artifacts`.

## Phase 1 — anonymous clean profile Cloudflare check

This proves Docker + Xvfb + Patchright Chrome can reach normal ChatGPT UI without a stale profile.

```bash
cd /home/spikkie/git/chatgpt_claudecode_workflow-2

./scripts/docker-bonnetjes-cloudflare-check.sh   --clean-only   --max-wait-seconds 300   --poll-seconds 10
```

Expected diagnostic result:

```json
{
  "status": "cloudflare_cleared_auth_ready",
  "cloudflare_cleared": true,
  "auth_ready": true,
  "challenge_detected": false,
  "composer_visible": true,
  "logged_in": false
}
```

`logged_in=false` is acceptable in this phase because the profile is intentionally anonymous.

## Phase 2 — create a clean logged-in host profile

```bash
cd /home/spikkie/git/chatgpt_claudecode_workflow-2

./scripts/docker-bonnetjes-clean-login-profile-bootstrap.sh
```

In the visible Chrome window:

1. Confirm Cloudflare clears.
2. Log in manually.
3. Confirm the ChatGPT composer is visible.
4. Close Chrome completely.

The script prints the exact `PROMPTBRANCH_HOST_PROFILE_DIR` path and follow-up Docker command.

## Phase 3 — test the logged-in profile inside Docker

Run the command printed by the bootstrap script. It has this shape:

```bash
PROMPTBRANCH_DOCKER_BROWSER_PROFILE=bonnetjes-cloudflare-parity PROMPTBRANCH_HOST_PROFILE_DIR="/absolute/path/to/.pb_profile_bonnetjes_manual_<timestamp>" PROMPTBRANCH_PROFILE_DIR=/app/profile PROMPTBRANCH_AUTH_READINESS_KEEP_OPEN_SECONDS=300 ./scripts/docker-browser-parity-cloudflare-check.sh   --max-wait-seconds 300   --poll-seconds 10
```

Expected logged-in result:

```json
{
  "status": "cloudflare_cleared_auth_ready",
  "cloudflare_cleared": true,
  "auth_ready": true,
  "challenge_detected": false,
  "logged_in": true,
  "composer_visible": true,
  "release_blocking": false
}
```

## Build-context hygiene gate

The selected `PROMPTBRANCH_HOST_PROFILE_DIR` is bind-mounted into the container. It must not be copied into the Docker image build context. `v0.1.103.9` enforces this with:

- `.dockerignore` wildcard exclusions for `.pb_profile*` and `.pb_profile_*`.
- A script guard that refuses unsafe profile paths under the repository.
- Bounded artifact export only through `/tmp/pb-challenge-artifacts`.

## Evidence handling

Use only:

```bash
./scripts/docker-browser-parity-export-challenge-artifacts.sh
```

Do not run:

```bash
docker cp "$CID:/app/debug_artifacts/." debug_artifacts/...
```

If no challenge artifacts exist, the exporter returns:

```json
{
  "ok": true,
  "status": "no_matching_artifacts"
}
```
