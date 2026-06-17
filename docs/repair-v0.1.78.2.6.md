# Repair v0.1.78.2.6 — Docker build cache/provenance guard

## Scope

Repair release `v0.1.78.2.6` adds deterministic Docker build-context, image-content, and running-container version provenance checks. It preserves the delete-frozen policy and the `--run-all-tests` behavior from `v0.1.78.2.5`.

## Reason

`v0.1.78.2.5` could install correctly on the host while Docker served an image tagged as the target version but containing stale `/app` files from the prior version. The release workflow must not trust the image tag alone.

## Implemented

- Docker Compose passes `PROMPTBRANCH_VERSION` and `PROMPTBRANCH_ARTIFACT_SHA256` as build args.
- Dockerfile records version/artifact labels and fails during build if `/app/VERSION`, `promptbranch_version.py`, or `pyproject.toml` do not match the target version.
- Release-control verifies host build-context version files before Docker build.
- Release-control probes built image content after normal cached build before starting the container.
- Release-control uses one bounded no-cache fallback only when the normal build or service provenance check is stale.
- Release-control probes running container content before trusting `/healthz`.

## Preserved boundaries

- No ChatGPT Project deletion.
- No secure delete protocol.
- No Project Source removal behavior change.
- No adoption/current mutation.
- No v0.1.79/k8s-game work.
