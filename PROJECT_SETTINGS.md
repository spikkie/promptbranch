# Project Settings

## Project identity and purpose

Promptbranch is a deterministic, artifact-first project orchestration and release-control system. Its primary product goal is a controlled problem-solving loop that moves from intent and evidence to bounded execution, validation, adoption, and ownership without granting implicit mutation authority.

The repository identifier is read from `docs/project/plan-state.json`. The intended ChatGPT Project binding is tracked in `.promptbranch-repo.json`, committed to Git, and included in release ZIPs. User-local project membership and adopted-artifact evidence remain runtime state derived from that tracked binding.

## Stable operating policy

- Keep the implementation KISS, CLI-first, deterministic, and fail-closed.
- Run browser automation and live release validation in Docker using the shared, explicitly selected browser profile.
- Preserve artifact-first baseline continuity and canonical release ZIP naming.
- Treat repository paths in policies and configuration as repository-relative unless a runtime command explicitly resolves them.
- Prefer new, clean state during active development. Do not add legacy fallback or migration behavior unless a recorded decision explicitly requires it.
- Keep ChatGPT Project deletion frozen until a separately authorized secure protocol exists.

## Authority model

`docs/project/project-authority-graph-v0.1.109.json` assigns exactly one owner to every declared project fact domain. `docs/project/promptbranch-behavioral-surface-v0.1.109.1.json` assigns stable identities and owners to executable instructions, skills/agents, tools, and prompts. Other files are projections, instructions, evidence, or runtime observations. There is no generic precedence chain and no last-write-wins rule.

Stable policy belongs here. Mutable release state belongs in `VERSION`, `docs/project/plan-state.json`, release configuration, or the project artifact registry as declared by the authority graph. `.promptbranch-repo.json` owns stable intended Project binding only and must never contain local paths, credentials, current artifact records, or upload evidence.

## Mutation boundaries

Read-only authority validation may read repository files, runtime identity files, registries, and external observation descriptors. It must not:

- change repository files;
- rewrite projections automatically;
- modify ChatGPT Project Settings;
- add, overwrite, or remove Project Sources;
- adopt artifacts;
- delete ChatGPT Projects;
- execute deployment or Kubernetes mutations.

Any future synchronization or correction capability requires an explicit later slice, a bounded execution contract, evidence, and adoption gating.

## Validation and adoption

Before a release can be claimed complete:

1. validate the project control surface;
2. validate the project authority graph in read-only mode;
3. run deterministic focused tests;
4. run the required direct and localhost release transports independently according to release policy;
5. require external live validation when requested by the release contract;
6. adopt only after all release gates pass and exact Project Source plus registry identity are verified.

Human-readable status documents are projections. A projection disagreement is drift and must block completion until corrected deliberately.

## Backlog authority

The machine-readable project backlog is `docs/backlog/backlog.json`. Ticket prose is stored under `docs/backlog/`. Only the backlog authority may classify an item as an open ticket.
