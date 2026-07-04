# Repair v0.1.103.10.52 — release-live project-ensure challenge fails fast and compose down remains operator-safe

## Scope

This repair preserves the Docker-only profile/challenge chain through v0.1.103.10.51 and fixes two runtime-safety gaps:

1. `live_project_ensure` now runs with release-live fail-fast challenge mode and must not enter manual-login wait after Cloudflare or backend-api 403 guardrail evidence.
2. `docker compose down` remains operator-safe without requiring `PROMPTBRANCH_VERSION` or `PROMPTBRANCH_SERVICE_IMAGE`; release/parity `up` paths still export versioned image identity explicitly.

## Invariants

- No host-CDP/session-manager revival.
- No copied-profile trust.
- No private backend-api operational dependency.
- `docker_live_profile_challenged` remains terminal for release-live browser steps.
