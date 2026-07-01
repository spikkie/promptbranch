# v0.1.103.10.21 — pb test api classification cleanup

Scope: report-only cleanup for `pb test api` classifications.

## Change

`pb test api` no longer classifies successful clear responses as:

- `browser_profile_busy`
- `rate_limited`
- `auth_challenge_or_cloudflare`

Classification now reads explicit top-level/detail status and error diagnostics instead of scanning the full response payload. This avoids false labels caused by successful response fields such as `challenge_detected=false`, `status=clear`, or historical conversation text that mentions profile contention.

## Non-goals

- No browser/session architecture change.
- No endpoint ordering change.
- No held-session reuse implementation.
- No Project Source mutation policy change.
- No Project deletion behavior change.
