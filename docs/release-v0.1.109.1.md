# Release v0.1.109.1

## Candidate

`v0.1.109.1 — Behavioral surface inventory and runtime authority resolver alignment`

## Baseline

Accepted/current baseline: `v0.1.109` / `chatgpt_claudecode_workflow-2_v0.1.109.zip`.

## Changes

- Repairs `pb project authority validate --include-runtime` so `project_registry_file(project_id)` resolves through the joined `.promptbranch-repo.json` identity and the authoritative project-scoped artifact registry.
- Adds `docs/project/promptbranch-behavioral-surface-v0.1.109.1.json` with stable IDs and owners for instructions, skills, agents, tools, and prompts.
- Adds `pb project behavioral-surface show` and `validate` with kind and consumer filters.
- Validates MCP manifest/schema/dispatcher/alias consistency, blocked-tool boundaries, skill-to-tool references, embedded skill projections, prompt contracts, owner symbols, and test mappings.
- Adds `docs/project/behavioral-surface.md` as the human-readable projection.
- Adds the behavioral registry as the tenth explicit project authority domain.
- Adds authority and behavioral-surface tests to mandatory full release-validation groups.

## Safety boundary

Inventory and validation are static and read-only. They perform no Project Source mutation, artifact adoption, Git mutation, remote ChatGPT Project Settings mutation, command execution, or automatic repair.

## Local candidate validation

- Focused authority/control/MCP/version suite: 93 passed.
- Expanded deterministic source suite: 138 passed across authority, behavioral surface, project control, MCP, version, and release-validation harness contracts. CLI, clean extraction, compilation, ZIP hygiene, and Artifact Guardian results are recorded in the candidate build report.
- Full direct, independent localhost, external ChatGPT live validation, Project Source upload, and adoption are not claimed by the candidate build.
