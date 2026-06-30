# Repair v0.1.103.6 — Docker parity artifact export safety

## Purpose

`v0.1.103.6` repairs the Docker parity diagnostic workflow after a manual `docker cp` of `/app/debug_artifacts/.` into the repo debug tree expanded recursively. The release remains diagnostic-only and does not enable Project Source mutation.

## Scope

- Add `scripts/docker-browser-parity-export-challenge-artifacts.sh`.
- Never copy `/app/debug_artifacts` wholesale.
- Stage only files matching `auth_readiness_auth_challenge_detected_*` inside the container at `/tmp/pb-challenge-artifacts`.
- Enforce bounded export with `PROMPTBRANCH_CHALLENGE_ARTIFACT_EXPORT_MAX_FILES` and `PROMPTBRANCH_CHALLENGE_ARTIFACT_EXPORT_MAX_BYTES`.
- Refuse host destinations inside the repo `debug_artifacts/` tree to prevent recursive copy growth when `/app/debug_artifacts` is bind-mounted from the repo.
- Preserve the v0.1.103.4/v0.1.103.5 Project Source mutation gate unchanged.

## Safe usage

```bash
PROMPTBRANCH_CHALLENGE_ARTIFACT_EXPORT_MAX_FILES=30 \
PROMPTBRANCH_CHALLENGE_ARTIFACT_EXPORT_MAX_BYTES=52428800 \
./scripts/docker-browser-parity-export-challenge-artifacts.sh
```

By default the host export target is outside the repository under `/tmp/promptbranch-docker-browser-parity-challenge-artifacts/<timestamp>`.

## Out of scope

- No Project Source mutation.
- No adoption/current claim.
- No attempt to bypass Cloudflare.
- No broad Docker debug tree export.
