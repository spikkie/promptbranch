# Repair v0.1.78.2.11 — Run-all profile seed preservation and strict rate-limit detection

This repair preserves the v0.1.78.2.10 Docker provenance guard, retained delete-frozen project policy, and run-all cooldown retry behavior while fixing two release-control defects observed during operator validation.

## Scope

- Preserve `.pb_profile_local_debug/` across release ZIP import so a freshly authenticated live-test seed profile is not deleted before `--run-all-tests` reaches ask-live/artifact/release-live.
- Continue treating `.pb_profile_local_debug_pools/` as disposable generated state; do not preserve pool slots across installs.
- Validate that the configured live seed profile directory exists before running live browser steps.
- Sanitize known Chromium singleton/DevTools files from the seed profile before cloning pool slots.
- Make run-all rate-limit retry detection strict, so generic text such as "No ChatGPT rate-limit evidence observed" does not trigger a false retry.
- Preserve Docker host/image/container/health provenance checks.
- Preserve ChatGPT Project deletion freeze.

## Out of scope

- Secure ChatGPT Project delete protocol.
- Project Source behavior changes.
- Artifact adoption/current mutation.
- v0.1.79 / k8s-game work.

## Validation intent

A candidate can only become accepted/current after release-control proves the full operator validation stack and adoption/current evidence confirms runtime, state artifact, state source, registry current, and consistency alignment.
