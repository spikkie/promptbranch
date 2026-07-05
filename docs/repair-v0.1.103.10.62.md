# v0.1.103.10.62 — split external ChatGPT live probes from mandatory product release validation

## Scope

This repair stops default `--run-all-tests` from calling the Cloudflare-gated ChatGPT live preflight endpoint. The release-control product validation path still runs deterministic full/direct, full/localhost reuse, import smoke, and artifact guard evidence. External ChatGPT live probes remain available only through explicit operator flags.

## Policy

Default product validation must not call `POST /v1/login-check` because that path can be blocked by ChatGPT/Cloudflare human-check state that Promptbranch cannot fix. Those live probes are no longer treated as mandatory product validation by default.

Explicit live validation remains available with:

```bash
--run-external-live-tests
```

or, when an operator wants adoption to require the live ChatGPT probe:

```bash
--require-chatgpt-live-validation
```

## Result semantics

When external live tests are not requested, release-control records these steps as `external_live_not_requested`:

- `live_profile_preflight`
- `live_project_ensure`
- `ask_live`
- `visual_artifact_roundtrip`
- `release_live`

These statuses are neither live passes nor product failures. They document that the external live probe was intentionally not executed.

## Non-goals

- No Cloudflare workaround.
- No host-CDP/session-manager.
- No copied-profile trust.
- No private backend-api operational dependency.
