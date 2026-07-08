# v0.1.103.10.72 — update project control surface active candidate and preserve LIVE_BLOCKED only when product validation is clean

## Scope

- Keep the `v0.1.103.10.69` repo-root `install.sh` strict all-all release gate.
- Keep the `v0.1.103.10.71` `live_bootstrap_guardrail` cascade normalization.
- Update project control-surface active candidate metadata to `v0.1.103.10.72`.
- Preserve adoption refusal when all-all validation is not `GO`.
- Preserve product-failure precedence: product validation failures produce `FIX`, even when external-live also blocks.
- Preserve `LIVE_BLOCKED` only for otherwise-clean product validation with external-live blockage.
- Do not bypass Cloudflare or rate limits.
- Do not reintroduce host-CDP/session-manager or copied-profile trust.

## Validation target

The focused validation must prove that the control surface is internally consistent and that a replay shape with product failures plus `live_bootstrap_guardrail` resolves to `FIX`, not `LIVE_BLOCKED`.
