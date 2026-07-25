# AGENTS.md

These instructions apply to coding and orchestration agents working in this repository.

## Read order

Before proposing or changing work, read these authorities in order of purpose, not precedence:

1. `PROJECT_SETTINGS.md` for stable project policy and mutation boundaries.
2. the single `docs/project/project-authority-graph-*.json` file declared by the control surface for fact-domain ownership and projection rules.
3. `docs/project/plan-state.json` for mutable project and slice state.
4. `VERSION` for the package/release version.
5. `.promptbranch-release.yml` for release lifecycle configuration.
6. `.promptbranch-repo.json` for the tracked intended Project binding.
7. the user-local project repository configuration and project artifact registry only when runtime membership or adopted-artifact evidence is required.
8. `docs/project/status.md`, `docs/project/plan.md`, and `docs/project/release-status.md` as human-readable projections to verify, never as competing owners.

## Fail-closed rules

- Do not infer an authoritative value when its declared owner is absent, unreadable, duplicated, or contradictory.
- Do not resolve conflicts by timestamp, file order, conversational memory, or last-write-wins behavior.
- Do not silently support stale authority formats.
- Report missing authority, ambiguous ownership, projection drift, and unresolved external state explicitly.
- Keep read-only validation free of repository, registry, Project Source, Project Settings, deployment, and Project-deletion mutations.

## Release work

- Read the release version from `VERSION`; do not duplicate it in agent instructions.
- Read accepted/current and active-slice state from `docs/project/plan-state.json`.
- Use the canonical artifact filename derived from repository release configuration.
- Keep repair releases scope-neutral unless an explicit normal-slice decision authorizes scope advancement.
- Run focused deterministic tests before broad live validation.
- Require both full direct and full localhost release evidence according to release-control policy.
- Never claim adoption from packaging, upload, or test success alone. Adoption requires the guarded adoption result and exact identity verification.

## Editing discipline

- Change the authoritative owner first.
- Update declared projections in the same change.
- Add or update deterministic drift tests.
- Preserve unrelated behavior and avoid broad refactors in narrow slices.
- Do not modify remote ChatGPT Project Settings in the authority-definition slice.

## Completion claims

A completion claim must identify:

- the authoritative files changed;
- the projections updated;
- the deterministic tests run;
- the live gates not run, when applicable;
- the artifact produced;
- whether adoption, Project Source mutation, Git commit, or Git push occurred.

Never claim work that evidence does not prove.
