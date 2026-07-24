# Promptbranch plan v0.1.109

## Goal

Define a precedence-free project authority graph and provide read-only validation of authoritative owners and projections.

## Deliverables

- `PROJECT_SETTINGS.md` with stable policy only.
- `AGENTS.md` with repository agent instructions that reference mutable authorities instead of duplicating them.
- `docs/project/project-authority-graph-v0.1.109.json` with exactly one authority per fact domain.
- `pb project authority show` and `pb project authority validate`.
- Deterministic regressions for missing, duplicate, drifted, and zero-mutation behavior.

## Authority domains

The graph covers release version, stable project policy, agent instructions, mutable plan state, release configuration, joined runtime identity, adopted artifact identity, external ChatGPT Project Settings, and the graph itself.

## Safety boundary

Validation is read-only. Remote Project Settings, Project Sources, registries, repository files, deployments, Kubernetes resources, and ChatGPT Projects are not mutated. Runtime and external domains may be reported as deferred or unresolved during static validation; they are never inferred from projections.

## Acceptance

Static validation must return `authority_consistent`, deterministic focused tests must pass, and the normal release gate must pass both full transports plus existing adoption checks.
