# v0.1.103.10.75 — release-live-continuous distinguishes missing bootstrap sentinel from backend guardrail and retries the real failed phase

KISS scope:

1. Keep v0.1.103.10.69 `install.sh` strict all-all gate.
2. Keep product-clean `LIVE_BLOCKED` classification.
3. Do not bypass Cloudflare or rate limits.
4. Do not report backend-api guardrail unless the explicit live bootstrap guardrail status is present.
5. If bootstrap sentinel is missing while ask sentinel succeeds, report `bootstrap_sentinel_missing_after_ask_success`.
6. Retry only the missing bootstrap phase once when auth readiness is clean, challenge-free, composer-visible, logged in, and scoped to the trusted conversation URL.
7. If retry still fails, return `LIVE_BLOCKED` with the precise bootstrap-sentinel status, not generic `live_bootstrap_guardrail`.
8. Preserve failed live steps and adoption refusal.
9. No host-CDP/session-manager and no copied-profile trust.

Candidate only until full all-all validation proves GO/adoption.
