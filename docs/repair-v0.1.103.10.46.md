# v0.1.103.10.46 — make docker_live_profile_challenged terminal for live test matrix and release-control

## Scope

- Keep accepted/current `v0.1.103.10.38` as baseline.
- Keep all-in-Docker only.
- Preserve `v0.1.103.10.40` explicit Docker live profile bootstrap.
- Preserve `v0.1.103.10.41` `.pb_profile_local_debug_pools` preservation.
- Preserve `v0.1.103.10.42` `/c/...` live conversation URL targeting.
- Preserve `v0.1.103.10.43` through `v0.1.103.10.45` fail-fast challenge handling.
- Make `docker_live_profile_challenged` terminal inside `pb test ask-live`.
- Use fixed-string/JSON-aware release-control challenge detection instead of the invalid regex path.
- Mark `visual_artifact_roundtrip` and `release_live` as skipped when `ask_live` proves the Docker live slot is challenged.

## Non-goals

- No host-CDP/session-manager.
- No copied-profile trust.
- No browser/session architecture redesign.
- No ChatGPT Project deletion.
