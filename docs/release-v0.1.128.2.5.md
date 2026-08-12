# v0.1.128.2.5 — Authoritative baseline auto-resolution repair

Fresh lifecycle proof no longer requires operator baseline-version bookkeeping. The launcher resolves adopted/current from the tracked project registry. Existing retries retain their attempt-bound baseline. An optional explicit baseline remains a fail-closed assertion. All v0.1.128.2 skills and prior runtime/timeout recovery behavior are preserved.
