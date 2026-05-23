# Release v0.0.261

## Baseline

Built from accepted repair baseline `chatgpt_claudecode_workflow_v0.0.260.1.zip`.

## Scope

Normal development release focused on service-script permission hardening after the strict v0.0.260.1 finalizer proved the real-candidate MVP path.

## Changes

- Bumped project/package version metadata to `v0.0.261` / `0.0.261`.
- Updated `chatgpt_claudecode_workflow_release_control.sh` to restore executable bits for repository shell entrypoints after ZIP install:
  - root-level `*.sh`
  - `scripts/**/*.sh`
  - `docker/**/*.sh`
- Added a pre-service fallback that attempts `chmod +x ./run_chatgpt_service.sh` before failing the service phase.
- Added regression coverage that imported ZIPs with non-executable shell scripts are normalized before later lifecycle phases.

## Validation

- Python compile check.
- Focused parser/version and shell-script regression tests.
- ZIP hygiene check.
- Extracted ZIP smoke check.

## Not claimed

- Project Source mutation.
- Git commit or push.
- Local adoption.
- Full browser suite.
