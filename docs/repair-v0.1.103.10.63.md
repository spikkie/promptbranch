# v0.1.103.10.63 — classify release-live-continuous first-ask Cloudflare challenge as LIVE_BLOCKED

## Problem

`v0.1.103.10.62` correctly split external ChatGPT live probes from default product release validation and correctly ran explicit external-live validation when requested. In the second explicit external-live run, product validation passed and `live_profile_preflight` passed, but `release-live-continuous` hit a Cloudflare/Docker live profile challenge during the first ask.

The release-control summary classified that result as `FIX`, which implies Promptbranch product/code repair is needed. The better operator verdict is `LIVE_BLOCKED`: deterministic product validation is healthy, but the external ChatGPT browser probe was blocked.

## Repair

Release-control summary classification now treats these external-live challenge statuses as external live blockage evidence:

- `docker_live_profile_challenged`
- `skipped_ask_live_docker_live_profile_challenged`
- `skipped_live_project_ensure_docker_live_profile_challenged`

The raw-log diagnostics also recognize `docker_live_profile_challenged` as an external browser challenge.

## Scope boundaries

- Keeps `v0.1.103.10.62` accepted/current as baseline.
- Keeps all-in-Docker only.
- Keeps explicit external-live flags.
- Does not bypass Cloudflare.
- Does not add host-CDP/session-manager.
- Does not copy browser profiles.
- Does not change deterministic product validation gates.
- Does not claim external live success when ChatGPT blocks the browser.
