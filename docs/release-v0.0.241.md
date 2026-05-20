# Release v0.0.241

Base release: v0.0.240.1

## Scope

Deterministic Docker service recreation and version-aware service verification.

## Changes

- Release control now recreates the Docker Compose service with `down --remove-orphans`, `build --pull`, and `up -d --force-recreate --remove-orphans`.
- Release control verifies `/healthz` reports the expected package/service version before considering service startup successful.
- Release control records service health, Docker Compose ps output, and before/after container inspect artifacts under `.pb_profile/release_logs/<version>/`.
- Direct `run_chatgpt_service.sh` usage now includes `--force-recreate` by default.

## Non-goals

No artifact intake, protocol, browser automation, or source-upload behavior changed.

## Validation

- `bash -n` on shell scripts.
- `py_compile` on touched tests.
- Focused shell-script regression tests.
- ZIP hygiene and CRC verification.
