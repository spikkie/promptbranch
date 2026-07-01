# v0.1.103.10.20 — pb test api avoids held-session self-conflicts

## Problem

`v0.1.103.10.19` proved the installed `pb test api` runner works, but full default mode held an auth-readiness session and then invoked unrelated browser-owning endpoints. Those calls failed with `browser_context_unavailable_held_auth_session_active`.

## Change

- Default runner order is serial browser mode.
- Projects/chats/debug/sources checks run without an intentionally held auth-readiness session.
- `/v1/ask` runs near the end.
- `/v1/auth-readiness` runs last by default and keeps the session closed unless `--hold-auth-session`/legacy `--keep-open` is passed.
- Busy profile failures are classified as `browser_profile_busy`.

## Out of scope

- No Project deletion.
- No Project Source mutation unless explicit flags are supplied.
- No v0.1.104.x host-CDP/session manager changes.
