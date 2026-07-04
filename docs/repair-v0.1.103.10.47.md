# Repair v0.1.103.10.47 — mid-run Cloudflare/backend-403 challenge is terminal

## Scope

- Keep all-in-Docker only.
- Preserve explicit Docker live profile bootstrap from v0.1.103.10.40.
- Preserve `.pb_profile_local_debug_pools` import preservation from v0.1.103.10.41.
- Preserve `/c/...` live conversation URL targeting from v0.1.103.10.42.
- Preserve release-live fail-fast challenge handling from v0.1.103.10.43 through v0.1.103.10.46.
- Treat mid-run backend 403 / Cloudflare challenge evidence during response wait as terminal `docker_live_profile_challenged`.

## Repair

The second v0.1.103.10.46 adoption run showed that the release-live slot could pass initial auth/composer checks and then hit Cloudflare/backend 403 while waiting for a response. That case was misclassified as a generic `TargetClosedError`, and the persisted conversation-history cooldown caused the ask-live matrix to keep waiting/retrying.

This repair adds fail-fast classification during response wait and exception handling:

- backend-api 403 observed in release-live fail-fast mode is recorded as challenge evidence;
- the 403 no longer writes `.conversation_history_rate_limit_until` in fail-fast release-live mode;
- `TargetClosedError` after observed backend 403 maps to `AuthChallengeRequiredError(challenge_type="docker_live_profile_challenged")`;
- root URL drift after observed backend 403 maps to `docker_live_profile_challenged`;
- Cloudflare token URLs such as `__cf_chl_tk` / `__cf_chl_f_tk` are challenge indicators.

## Non-goals

- No host-CDP/session-manager revival.
- No copied-profile trust.
- No weakening of live validation.
- No ChatGPT Project deletion.
