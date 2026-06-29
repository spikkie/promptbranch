# Release candidate v0.1.104.8

`v0.1.104.8` is a repair-only candidate for `v0.1.104 — Sandbox mutation verification and rollback evidence gate`.

It is diagnostic/debug oriented. It preserves the sandbox mutation verification behavior and adds clearer failure classification when ChatGPT auth/challenge readiness blocks browser automation before Project Sources can render.

## Added

- `promptbranch.auth_readiness_snapshot` evidence with URL, title, text preview, driver, profile, browser mode, and challenge indicators.
- `auth_challenge_blocking_before_project_sources` failure status for Project Source operations blocked by ChatGPT/Cloudflare/auth challenge state.
- Structured CLI payload propagation for service error details when source add fails with machine-readable error detail.

## Preserved

- `v0.1.104` sandbox mutation verification and rollback evidence gate.
- `v0.1.104.1` project-remove frozen scheduler timeout repair.
- No scope advancement to `v0.1.105`.
- No Project Source mutation when auth readiness is blocked.
- No Cloudflare bypass.
