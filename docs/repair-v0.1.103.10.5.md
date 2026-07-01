# v0.1.103.10.5 — standard browser profile ownership repair

## Problem

`v0.1.103.10.4` could fail before Cloudflare validation because the standard browser profile directory existed as `root:root`:

```text
.pb_profile/browser/default
```

Chrome then could not create `SingletonLock` and aborted with `Permission denied` / `Failed to create a ProcessSingleton`.

## Cause

A Docker bind mount can create the host-side mount target before the host Chrome bootstrap has created it. When Docker creates that missing host path, the resulting empty directory can be owned by root.

## Repair

- `scripts/pb-browser-profile-bootstrap.sh` now prepares the profile directory before launching host Chrome.
- Empty non-writable placeholder directories are removed and recreated by the host user.
- Non-empty non-writable profile directories fail fast with an explicit `sudo chown -R $(id -u):$(id -g)` repair command instead of letting Chrome fail later.
- `scripts/docker-browser-parity-cloudflare-check.sh` prepares and exports an absolute `PROMPTBRANCH_HOST_PROFILE_DIR` before `docker compose up` so the bind mount target is created by the operator user.

## Scope boundaries

No Project Source mutation is enabled. No Cloudflare envelope behavior is changed. Old Bonnetjes wrapper names remain compatibility wrappers. This repair only fixes standard browser profile ownership/writability handling.
