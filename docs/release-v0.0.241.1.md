# Release v0.0.241.1

Repair release for v0.0.241.

## Base release

- `v0.0.241`

## Reason

`v0.0.241` correctly recreated the Docker Compose service as the host UID/GID, but the non-root container process could not import `/app/promptbranch_browser_auth/client.py` when copied source files had restrictive permissions. The runtime failed with `PermissionError: [Errno 13] Permission denied` during Uvicorn startup.

## Files changed

- `Dockerfile`
- `.dockerignore`
- `VERSION`
- `pyproject.toml`
- version metadata/test surfaces
- `tests/test_promptbranch_shell_scripts.py`
- `docs/release-v0.0.241.1.md`

## Validation performed

- `bash -n` on shell scripts
- Python compile checks
- focused Docker permission and dockerignore tests
- version smoke
- ZIP CRC and hygiene checks

## Scope confirmation

No normal release scope was advanced. This repair only fixes Docker runtime permissions and build-context hygiene for the intended v0.0.241 Docker recreate behavior.
