# v0.1.103.10.70 — classify release-live-continuous bootstrap guardrail as external live blocked

## Scope

This repair keeps the v0.1.103.10.69 repo-root `install.sh` strict all-all release gate unchanged.

It changes release-control final classification only: when `release-live-continuous` reports `live_bootstrap_guardrail` due to backend-api/rate-limit guardrail telemetry, the all-tests final verdict is `LIVE_BLOCKED`, not product `FIX`.

## Reason

The all-all gate must still refuse adoption when explicit external-live validation fails, but this condition is an external ChatGPT/browser/rate-limit guardrail, not proof that Promptbranch product code requires repair.

## In scope

- Add `live_bootstrap_guardrail` to external-live blocked statuses.
- Add `skipped_blocked_by_live_bootstrap_guardrail` to external-live blocked statuses.
- Preserve failed/skipped live step evidence.
- Preserve artifact guard pass semantics.
- Preserve adoption refusal when `--adopt-after-validation` is used and external-live fails.

## Out of scope

- No Cloudflare or rate-limit bypass.
- No host-CDP/session-manager.
- No copied-profile trust.
- No ChatGPT Project deletion.
- No release-control flow redesign.
- No claim that external-live validation passes.
