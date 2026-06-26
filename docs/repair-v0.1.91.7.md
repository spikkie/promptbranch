# Repair v0.1.91.7 — Pre-source-add Docker no-cache build-context freshness repair

## Base and continuity

Repair-only continuation of the `v0.1.91` repair stack. This candidate builds on the `v0.1.91.6` repair state and preserves the earlier repairs:

- `v0.1.91.1` ask-live first-turn retry recovery
- `v0.1.91.2` run-all pretty JSON / live-step aggregation repair
- `v0.1.91.3` Docker service recreate/version verification hardening
- `v0.1.91.4` clean-system pre-source-add service bootstrap
- `v0.1.91.5` `live_project_ensure` aggregation terminal-line repair
- `v0.1.91.6` adopt-after-validation run-all evidence-reuse report path repair

No normal slice advances.

## Reason

The `v0.1.91.6` pre-source-add bootstrap reached Docker build but failed because Docker reused a cached `COPY . .` layer from `v0.1.91.5` while the build arg expected `0.1.91.6`. The Dockerfile version guard correctly failed the build before a stale service image could start.

## Scope

This repair changes only the pre-source-add Docker bootstrap path:

- invoke Docker Compose with explicit `--project-directory "$repo_root"`
- use the absolute compose file path
- build the candidate service with `--no-cache --pull`
- record repo-root version surfaces and resolved Compose config before build
- classify Docker build-context version mismatch as `pre_source_add_docker_build_context_version_mismatch`
- stop immediately on Docker build failure before health probing

Out of scope: live/browser behavior, validation semantics, Project Source mutation semantics, adoption/current semantics, Project deletion behavior, and localhost/evidence-reuse policy.

## Validation performed

Focused validation covered the pre-source-add service bootstrap contract, no-cache build command, explicit repo-root Compose invocation, build-context version-surface diagnostics, version consistency, and project control surface.
