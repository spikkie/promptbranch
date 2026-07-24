# Release v0.1.109

## Candidate

`v0.1.109 — PROJECT_SETTINGS.md, AGENTS.md and project authority-graph definition`

## Changes

- Added stable project policy and agent operating instructions.
- Added a machine-readable, precedence-free authority graph.
- Added read-only authority show/validate CLI commands.
- Added fail-closed missing/ambiguity/projection-drift classification.
- Added static handling for deferred runtime identity, artifact registry, and external Project Settings observation domains.
- Added deterministic zero-mutation and drift tests.

## Not performed by this candidate build

No remote ChatGPT Project Settings mutation, Project Source mutation, artifact adoption, Git push, deployment, Kubernetes mutation, or ChatGPT Project deletion is claimed.

## Local validation

- 279 focused/relevant deterministic tests passed.
- `pb project authority validate --json` returned `authority_consistent`.
- Project control-surface and next-slice validation passed from a clean extraction.
- Installed-module smoke resolved package version and the new authority module.
- Full browser/live release-control and adoption were not run in the build environment.
