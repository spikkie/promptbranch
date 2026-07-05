# v0.1.103.10.60 — configure Docker live-slot service with trusted conversation URL before preflight

## Scope

- Baseline remains accepted/current `v0.1.103.10.38`.
- Preserve cumulative Docker/live repairs from `v0.1.103.10.40` through `v0.1.103.10.59`.
- Keep `release-live-continuous` routed through the Docker service.
- Configure the Docker live-slot service with a trusted `/g/.../c/...` conversation URL before `live_profile_preflight`.
- Refuse to start the Docker live-slot service at bare `https://chatgpt.com/` when no trusted conversation URL is available.

## Fix

`v0.1.103.10.59` mapped the release-live slot to `/app/profile`, but `CHATGPT_PROJECT_URL` still defaulted to `https://chatgpt.com/` during live-slot service recreation. This candidate resolves a trusted conversation URL before service recreation and exports both:

```bash
CHATGPT_PROJECT_URL=<trusted /g/.../c/... URL>
PROMPTBRANCH_HOST_PROFILE_DIR=.pb_profile_local_debug_pools/release-live/slots/slot-1
```

If no trusted `/c/...` URL is resolvable, release-control writes `live_preflight_target_url_missing` and skips live browser phases without falling back to ChatGPT root.

## Non-goals

- No Cloudflare bypass.
- No host-CDP/session-manager.
- No copied-profile trust.
- No private backend-api operational dependency.
