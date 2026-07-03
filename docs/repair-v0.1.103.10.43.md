# Repair v0.1.103.10.43 — release live browser challenge fails fast without manual-login wait

## Scope

- Keep accepted/current `v0.1.103.10.38` as baseline authority.
- Keep all-in-Docker only.
- Preserve `v0.1.103.10.40` explicit Docker live profile bootstrap.
- Preserve `v0.1.103.10.41` `.pb_profile_local_debug_pools` preservation across release ZIP import.
- Preserve `v0.1.103.10.42` `/c/...` conversation URL targeting for live steps.
- Add release-live fail-fast behavior for Cloudflare/Just-a-moment challenge detection.

## Behavior

Release-control live commands set `PROMPTBRANCH_RELEASE_LIVE_FAIL_FAST_ON_CHALLENGE=1` and `CHATGPT_FAIL_FAST_ON_CHALLENGE=1`. In that mode, the browser client checks for challenge state immediately after initial challenge settling and again before manual-login polling. If the page is still a challenge, it raises an authentication challenge with `challenge_type=docker_live_profile_challenged`. The browser context is finalized normally and release-control records a structured failure instead of leaving headed Chrome open for a 600-second manual-login wait.

## Non-goals

- No host-CDP/session-manager revival.
- No copied-profile trust.
- No browser/session architecture redesign.
- No Project Source mutation behavior change.
- No ChatGPT Project deletion.
