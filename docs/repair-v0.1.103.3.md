# Repair v0.1.103.3 — passive auth-readiness runtime-client wiring repair

## Baseline

`v0.1.103.2` introduced `/v1/auth-readiness`, but the endpoint failed live because the Promptbranch runtime imports `promptbranch_browser_auth.ChatGPTBrowserClient`, while the passive auth method existed only on the compatibility `chatgpt_browser_auth` client.

## Scope

- Add `run_passive_auth_readiness()` to `promptbranch_browser_auth/client.py`.
- Add the internal passive operation and auth readiness state probe to the runtime client.
- Preserve passive behavior: no Login click, no Google auth flow, no hidden manual-login wait, and no Project Source mutation.
- Add focused regression coverage proving the runtime client exposes the passive-auth method.

## Out of scope

- Cloudflare bypass or challenge solving.
- Project Source mutation.
- Artifact adoption/current mutation.
- Docker VNC/noVNC/CDP work.
- Host-CDP repair-line changes.
- ChatGPT Project deletion.

## Validation

Focused local validation only. Live seeded-profile Docker auth-readiness remains pending operator execution.
