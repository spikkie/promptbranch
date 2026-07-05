# v0.1.103.10.61 — classify Docker live preflight challenge as external live challenge and stop browser-repair loop

## Baseline

Accepted/current remains `v0.1.103.10.38`. This candidate preserves the cumulative repair line through `v0.1.103.10.60` and does not claim adoption.

## Scope

This repair deliberately stops adding browser-flow changes for Cloudflare/human-check handling. The Docker live path remains all-in-Docker, uses the explicit release-live slot, and keeps the trusted `/g/.../c/...` target. If Docker live preflight returns `auth_challenge_required` or a `docker_standard_profile_challenged`/human-check marker, release-control now classifies that as an external live browser challenge.

## Behavior

- `live_profile_preflight` writes status `live_external_browser_challenge` for Docker 409/auth challenge evidence.
- Live cascade steps are skipped with `skipped_live_external_browser_challenge`.
- `import_smoke` and `artifact_guard` still execute after the structured external block.
- The all-tests summary can now emit `final_verdict: LIVE_BLOCKED` with `external_live_blocked: true` and `product_failure_count: 0`.
- Adoption remains refused unless final verdict is `GO`.
- The live-slot Docker recreate trace no longer prints a duplicated/conflicting `CHATGPT_PROJECT_URL` value.

## Non-goals

No new URL strategy, timing change, browser flag, copied profile, host-CDP, session-manager, or private backend-api dependency was added.
