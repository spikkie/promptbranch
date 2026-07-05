# Repair v0.1.103.10.58 — extract live preflight warmup URL from login-check url field

## Scope

This repair keeps the all-in-Docker Patchright path and the cumulative v0.1.103.10.40–10.57 release-live repairs.

## Change

`run_all_extract_conversation_url_from_log()` now accepts a top-level `url` field when, and only when, it is already a ChatGPT `/c/...` conversation URL. This matches `pb login-check` output from live profile preflight.

`release-live-continuous` no longer falls back to bare `https://chatgpt.com/` when the warmup conversation URL cannot be extracted. Missing warmup URL is now terminal with `live_preflight_warmup_url_missing`.

## Invariant

The release-live continuous path must start from the trusted URL proven by `live_profile_preflight`, not from ChatGPT root.
