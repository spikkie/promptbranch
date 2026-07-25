# Release v0.1.109.1.1

## Candidate

`v0.1.109.1.1 — Tracked repository Project binding and runtime evidence separation`

## Baseline

Accepted/current: `v0.1.109`.

## Changes

- Commits and packages the authoritative `.promptbranch-repo.json` Project binding.
- Reclassifies `repository.project_identity` as required repository-file authority.
- Validates binding schema, Project URL, repository ID, canonical artifact pattern, supported fields, and authority-graph alignment.
- Makes `pb project join` rebuild user-local configuration from the tracked binding without requiring repeated Project arguments.
- Fails closed when supplied join arguments differ from tracked authority.
- Keeps adopted artifact and exact Project Source evidence outside Git.
- Updates release ZIP import so the candidate binding replaces the checkout projection instead of being excluded or preserved.
- Adds `docs/migrations/tracked-project-binding-v0.1.109.1.1.md` for other projects.

## Adoption status

Candidate only. Full direct, independent localhost, external live validation, Artifact Guardian, and guarded adoption remain required.
