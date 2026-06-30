# v0.1.103.9 — Bonnetjes Cloudflare parity profile hygiene

## Status

Candidate only. Not accepted/current.

## Scope

`v0.1.103.9` keeps the working Bonnetjes Cloudflare parity browser mode unchanged and adds the profile/build-context hygiene required before downstream testing.

## Changes

- Adds `.dockerignore` exclusions for `.pb_profile*`, `.pb_profile_*`, `debug_artifacts/`, and `*.zip`.
- Keeps `PROMPTBRANCH_HOST_PROFILE_DIR` as a bind-mounted profile source for `/app/profile`.
- Adds a build-context guard to `scripts/docker-browser-parity-cloudflare-check.sh` so repository-local profiles are allowed only when excluded by `.dockerignore`.
- Fixes `scripts/docker-browser-parity-export-challenge-artifacts.sh` so no challenge artifacts is a successful no-op: `status=no_matching_artifacts`.
- Adds `scripts/docker-bonnetjes-clean-login-profile-bootstrap.sh` for creating a clean visible host Chrome login profile.
- Documents the full Cloudflare parity test phase in `docs/bonnetjes-cloudflare-parity-test-procedure.md`.

## Out of scope

- Project Source mutation.
- Login automation.
- Google login clicking.
- Artifact adoption.
- Full release-control adoption.

## Test procedure

See `docs/bonnetjes-cloudflare-parity-test-procedure.md`.
