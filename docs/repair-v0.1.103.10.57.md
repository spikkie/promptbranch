# Repair v0.1.103.10.57 — release-live-continuous trusted warmup URL

## Scope

- Keep accepted/current baseline `v0.1.103.10.38`.
- Keep all-in-Docker only.
- Preserve the cumulative `10.40`–`10.56` release-live repairs.
- Keep `release-live-continuous` wired into real CLI dispatch.
- Start `release-live-continuous` auth/warmup from the conversation URL already validated by `live_profile_preflight`, not bare `https://chatgpt.com/`.
- No host-CDP/session-manager.
- No copied-profile trust.
- No private backend-api operational dependency.

## Rationale

`v0.1.103.10.56` proved the new command dispatch works, but the continuous operation still opened the slot profile at bare `https://chatgpt.com/` for its initial auth check. The same slot had just passed preflight on a known `/g/.../c/...` conversation URL. This slice reuses that trusted URL as the warmup target.

## Expected behavior

- `live_profile_preflight` extracts a known conversation URL from login-check output.
- Release-control passes it to `pb test release-live-continuous --warmup-conversation-url`.
- The browser client temporarily uses that URL for the initial auth check.
- Project ensure, bootstrap, and first ask still run in one continuous browser session.
- If the warmup URL is challenged, the operation returns `docker_live_profile_challenged` immediately.
