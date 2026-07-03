# v0.1.103.10.36 — missing live seed profile is non-blocking for run-all release validation

## Problem

`v0.1.103.10.35` fixed release-control auth bootstrap and held-session clearing. The remaining release-control failure was in the extra live/artifact/import/guard section: `.pb_profile_local_debug` was missing, so release-control marked `live_profile_preflight` and its dependent live-only steps as failed.

That made adoption fail even though the release-blocking validation paths had passed: Project Source add, full direct validation, reused localhost validation evidence, import smoke, and artifact guard.

## Repair

When `.pb_profile_local_debug` is missing, release-control now records:

- `live_profile_preflight`: `status=profile_seed_missing`, `ok=true`, `exit_code=0`
- `live_project_ensure`: `status=live_profile_seed_missing`, `ok=true`, `exit_code=0`
- `ask_live`: `status=live_profile_seed_missing`, `ok=true`, `exit_code=0`
- `visual_artifact_roundtrip`: `status=live_profile_seed_missing`, `ok=true`, `exit_code=0`
- `release_live`: `status=live_profile_seed_missing`, `ok=true`, `exit_code=0`

If the live seed profile exists but fails login/authentication, the existing blocking behavior is preserved.

## Scope boundaries

- Keeps `v0.1.103.10.35` auth bootstrap and held-session clear behavior.
- Keeps full direct/full localhost validation release-blocking.
- Keeps Project Source add release-blocking.
- Keeps import smoke and artifact guard release-blocking.
- Does not copy or synthesize `.pb_profile_local_debug`.
- Does not change browser/session architecture.
- Does not enable default Project Source mutation.
- Does not delete ChatGPT Projects.
