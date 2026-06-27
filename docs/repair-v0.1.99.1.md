# Repair v0.1.99.1 — Docker build-context freshness repair

## Base release

```text
base candidate: chatgpt_claudecode_workflow-2_v0.1.99.zip
repair candidate: chatgpt_claudecode_workflow-2_v0.1.99.1.zip
accepted/current baseline before repair: chatgpt_claudecode_workflow-2_v0.1.98.zip
normal slice preserved: v0.1.99 — Rolling slice horizon and architecture-decision protocol
scope advanced: false
next normal slice after acceptance: v0.1.100 — First controlled read-only validation command execution
```

## Reason

The `v0.1.99` release-control run failed before Project Source add because the pre-source-add Docker service build copied stale `v0.1.98` version surfaces into `/app` while the host repo and candidate ZIP contained `v0.1.99`. Operator diagnostics proved a minimal no-cache Docker context probe still saw `v0.1.98`; after touching `VERSION`, `promptbranch_version.py`, and `pyproject.toml`, the no-cache build passed.

Root cause class: deterministic ZIP-installed files retained fixed mtimes and same-size version updates, allowing Docker/BuildKit local build-context freshness to miss the current candidate contents. Release-control also let the Docker build failure degrade to a generic service health failure.

## Changes

- Refresh safe repo-local Docker build-context mtimes before service image builds.
- Compute a source fingerprint from `VERSION`, `promptbranch_version.py`, and `pyproject.toml`.
- Pass `PROMPTBRANCH_SOURCE_FINGERPRINT` into Docker Compose builds.
- Consume the fingerprint before `COPY . .` so candidate source changes invalidate the build lineage.
- Verify both version surfaces and source fingerprint after `COPY . .`.
- Use explicit build followed by `docker compose up --no-build` for pre-source-add bootstrap.
- Fail fast/classify Docker build-context fingerprint/version mismatch instead of continuing to a generic service unavailable error.

## Out of scope

- No read-only validation command execution.
- No correction planning.
- No file mutation by the loop engine.
- No deployment, Kubernetes mutation, Project Source behavior change, artifact adoption behavior change, or ChatGPT Project deletion.
- No change to the `v0.1.99` rolling slice horizon other than repair metadata.

## Validation target

Focused candidate validation must cover shell syntax, Dockerfile/Compose declaration checks, control-surface validation, version surfaces, Artifact Guardian, and artifact verify. Full release-control/adoption remains required before this repair can be called accepted/current.
