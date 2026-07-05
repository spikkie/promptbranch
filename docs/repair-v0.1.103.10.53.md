# v0.1.103.10.53 — release-live bootstrap 429/guardrail is terminal before ask_live

## Scope

This repair keeps the Docker-only cumulative release-live chain and makes live conversation bootstrap telemetry release-blocking before `ask_live` opens another browser context.

## Behavior

If the live bootstrap returns a `/c/...` conversation URL but telemetry contains any of:

- `rate_limit_modal_detected=true`
- `conversation_history_429_seen=true`
- `backend_api_guardrail_seen=true`
- backend-api guardrail events

release-control marks the bootstrap as terminal guardrail evidence, skips `ask_live`, `visual_artifact_roundtrip`, and `release_live` with `skipped_blocked_by_live_bootstrap_guardrail`, then continues with `import_smoke` and `artifact_guard`.

## Invariants

- no host-CDP/session-manager
- no copied-profile trust
- no private backend-api operational dependency
- same explicit release-live slot remains the actor for project ensure, bootstrap, ask, visual, and release-live
