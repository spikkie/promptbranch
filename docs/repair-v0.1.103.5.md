# v0.1.103.5 — Docker parity true keep-open browser session mode

Status: candidate only, not accepted/current.

This repair continues the Docker browser parity investigation after `v0.1.103.4` proved the Project Source mutation guard works but the `keep_open=true` path still depended on interactive stdin. In service/API mode stdin is not interactive, so the browser context closed immediately and the challenge-clear observation was invalid.

## Scope

- Replace stdin-based passive auth `keep_open` with service-side held browser context logic.
- Hold the context for `PROMPTBRANCH_AUTH_READINESS_KEEP_OPEN_SECONDS` seconds, default `300`.
- Add `/v1/auth-readiness/session/status` to inspect the held context.
- Reuse the held context for subsequent `/v1/auth-readiness` calls while it is alive.
- Add `--keep-open` and `--no-recreate` to `scripts/docker-browser-parity-auth-readiness.sh`.
- Capture JSON/HTML/screenshot artifacts when passive auth-readiness detects a challenge.
- Preserve the guarded Project Source mutation gate unchanged.

## Out of scope

- Project Source mutation.
- Artifact adoption/current.
- Deployment or Kubernetes mutation.
- ChatGPT Project deletion.

## Validation

Focused compile and API/script tests are expected for this candidate. Live Docker challenge-clear behavior remains operator-side validation.
