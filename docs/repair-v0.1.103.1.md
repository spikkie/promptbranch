# v0.1.103.1 — Docker browser parity diagnostic envelope

Status: candidate only, not accepted/current.

## Baseline

Built on top of `chatgpt_claudecode_workflow-2_v0.1.103.zip`.

## Scope

- Adds a Docker browser diagnostic mode named `docker-browser-parity`.
- Preserves the existing default Promptbranch Docker profile path `/app/.pb_profile`.
- Allows diagnostic mode to switch to `/app/profile`, matching the reference Docker browser pattern.
- Exposes Docker browser runtime metadata through `/healthz` and `/v1/docker/browser-runtime`.
- Adds `scripts/docker-browser-parity-auth-readiness.sh` to run a diagnostic-only auth-readiness probe.
- Adds `.pb_profile_docker/` to generated/local state exclusions.

## Out of scope

- No Cloudflare bypass.
- No Project Source mutation.
- No artifact adoption/current mutation.
- No release-control host-CDP changes.
- No ChatGPT Project deletion.

## Validation

Focused validation for this candidate should include shell syntax, Python compile,
container API tests, shell-script tests, version tests, control-surface tests, ZIP
hygiene, and Artifact Guardian.
