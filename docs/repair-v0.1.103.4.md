# Repair v0.1.103.4 — Docker parity guarded Project Source mutation test

## Status

Candidate only. Not accepted/current.

## Scope

This diagnostic repair keeps Docker browser parity narrow and guarded. It adds an explicit Project Source mutation gate for Docker parity mode and requires passive auth-readiness before any `/v1/project-sources` mutation is attempted.

## Changes

- `POST /v1/project-sources` now fails closed in `PROMPTBRANCH_DOCKER_BROWSER_PROFILE=docker-browser-parity` unless `PROMPTBRANCH_ALLOW_PROJECT_SOURCE_MUTATION=1` is present.
- Docker parity Project Source mutation now runs passive `/v1/auth-readiness` first. Mutation proceeds only when `logged_in=true`, `challenge_detected=false`, `composer_visible=true`, and `release_blocking=false`.
- Docker runtime metadata now reports profile UID/GID, service UID/GID, writability, write-probe result, and whether Project Source mutation is explicitly allowed.
- Added `scripts/docker-browser-parity-guarded-project-source-test.sh` for explicit, diagnostic-only guarded source upload testing.

## Out of scope

- No Cloudflare bypass.
- No automatic login.
- No hidden manual-login wait.
- No release adoption/current mutation.
- No broad release-control rewrite.
- No ChatGPT Project deletion.

## Validation

Local focused validation was run before packaging. Live Docker Project Source mutation was not run in the artifact build environment.
