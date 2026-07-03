# v0.1.103.10.45 — repair package version surface for Docker build context coherence

## Scope

- Keep accepted/current `v0.1.103.10.38` as the adoption baseline.
- Keep all-in-Docker only; do not revive host-CDP/session-manager.
- Preserve the cumulative `v0.1.103.10.40` through `v0.1.103.10.44` release-live repairs.
- Repair the candidate package version surface so `VERSION`, `promptbranch_version.py`, and `pyproject.toml` all report `0.1.103.10.45` / `v0.1.103.10.45`.
- Keep Docker build context verification strict; do not weaken the stale-context guard.

## Root cause

`v0.1.103.10.44` packaged `VERSION` and `promptbranch_version.py` as `0.1.103.10.44`, but left `pyproject.toml` at `0.1.103.10.43`. The package installer therefore reported the old package version, and Docker build-context verification failed before pre-source-add validation.

## Behavior

Docker build-context validation should now see coherent values across:

- `VERSION`
- `promptbranch_version.py`
- `pyproject.toml`

The stale-context guard remains release-blocking if a future candidate has mismatched version surfaces.
