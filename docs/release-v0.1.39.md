# Release v0.1.39

## Scope

Read-only ChatGPT rate-limit diagnostics and backend-api surface documentation.

## Changes

- Added `pb debug rate-limit --json`.
- Captures visible conversation-history rate-limit modal text without acknowledging or bypassing it.
- Captures observed `/backend-api/*` `403` and `429` responses with redacted URL metadata, `retry-after` when available, safe content type, and short body previews only for guardrail responses.
- Persists cooldown state when backend guardrail responses are observed.
- Treats the rate-limit modal timeout as a non-retryable `RateLimitDetectedError` so service-level retry loops do not amplify the restriction.
- Added a documented inventory of current ChatGPT `/backend-api` surfaces used or observed by Promptbranch.

## Safety boundary

This release does not bypass ChatGPT rate limits. It detects the guardrail, reports `status=rate_limited`, and instructs Promptbranch to pause further ChatGPT calls until the cooldown or `retry-after` window expires.

## Validation

- Parser accepts `pb debug rate-limit --json`.
- Parser accepts `pb debug rate-limit --probe-backend --wait-ms ... --keep-open --json`.
- Browser client helper tests cover backend API URL redaction and cooldown persistence for `403`/`429` guardrail responses.
- CLI dispatch test verifies the command emits JSON and returns a rate-limit exit code when status is `rate_limited`.
