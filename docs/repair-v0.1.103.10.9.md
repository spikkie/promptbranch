# Repair v0.1.103.10.9 — pb ask reuses held auth-ready browser session

## Trigger

After `v0.1.103.10.7`/`v0.1.103.10.8` standard-browser auth-readiness passed, a plain `pb ask` started a second persistent browser context against the same `/app/profile`. The ask path cleared `SingletonLock`, `SingletonSocket`, and `SingletonCookie` while the auth-readiness browser context was still held open, then navigated a fresh context into a Cloudflare challenge.

## Scope

- Reuse an active held auth-readiness session for `pb ask` when the profile, browser driver, and browser channel match.
- Probe held-session status before ask submission.
- Submit through the held page when status is `auth_preflight_ready`, `composer_visible=true`, `logged_in=true`, and no challenge is detected.
- Refuse singleton cleanup while a compatible held auth-readiness session is active.
- If the held session is challenged, stale, or invalid, close it cleanly and fail fast instead of opening a competing context.

## Out of scope

- ChatGPT Project Source mutation.
- v0.1.104.x host-CDP session manager.
- Browser fingerprint/envelope changes.
- ChatGPT Project deletion.
- Artifact adoption/current mutation.
- Git commit or push.

## Validation focus

- Held auth-ready ask path reuses the existing page/context.
- No `Singleton*` cleanup occurs while a compatible held session is active.
- Challenged held sessions are closed and reported as fail-fast ask results.
