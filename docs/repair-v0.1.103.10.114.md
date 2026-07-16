# Repair v0.1.103.10.114

## Continuous live-profile resolution and causal-submit evidence

`v0.1.103.10.113` live-proved collision-free indexed-family replacement but remained unadopted after a false-negative visual-artifact submit-causality result. This repair preserves the overwrite implementation unchanged.

### Contract

1. A pool root may be used with `--profile-lease`; an exact `.../slots/slot-N` profile is used without profile leasing.
2. Visual-artifact and release-live validation share one exact physical slot.
3. Current ChatGPT submission is causal when post-click evidence includes `POST /backend-api/f/conversation`, Sentinel prepare/finalize, or `IS_STREAMING`.
4. A structurally valid `promptbranch.ask.reply` from a newly created assistant turn beyond the pre-submit baseline is acceptable causal response evidence.
5. Stable idle valid responses return early instead of waiting through the long fallback.
6. Cloudflare classification requires actual challenge evidence.
7. `full_localhost` executes independently and may not reuse direct browser/source lifecycle evidence.
8. Adoption remains fail-closed until every mandatory gate passes.
