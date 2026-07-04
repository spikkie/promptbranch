# Repair v0.1.103.10.51 — versioned Docker image tag propagation for parity/check compose paths

## Scope

Preserve the cumulative Docker/Patchright live-profile and backend guardrail repairs through v0.1.103.10.50, then fix the remaining Docker traceability leak where parity/check compose paths could still build or run `promptbranch-service:local` when `PROMPTBRANCH_SERVICE_IMAGE_TAG` was not set.

## Changes

- `docker-compose.chatgpt-service.yml` now requires release/run/parity scripts to provide `PROMPTBRANCH_VERSION` and `PROMPTBRANCH_SERVICE_IMAGE`; it no longer silently falls back to `unknown` or `local` during candidate validation.
- `scripts/docker-browser-parity-cloudflare-check.sh` derives the versioned image tag from `PROMPTBRANCH_SERVICE_IMAGE_TAG`, `PROMPTBRANCH_VERSION`, or `VERSION`, then exports `PROMPTBRANCH_SERVICE_IMAGE_TAG`, `PROMPTBRANCH_VERSION`, and `PROMPTBRANCH_SERVICE_IMAGE` before invoking Compose.
- `scripts/pb-docker-browser-profile-bootstrap.sh` refuses a silent `promptbranch-service:local` fallback when both `PROMPTBRANCH_SERVICE_IMAGE_TAG` and `VERSION` are missing.

## Non-goals

- No host-CDP/session-manager revival.
- No copied-profile trust.
- No profile reset automation.
- No change to the v0.1.103.10.50 backend-api guardrail terminal behavior.
