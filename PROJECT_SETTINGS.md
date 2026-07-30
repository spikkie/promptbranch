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

## PBAI-001 application architecture policy

The tracked AI application declaration is `.promptbranch-ai.json`; its authoritative object registry is `.promptbranch/ai-registry.json`, validated against `promptbranch_protocol/schemas/application.architecture.schema.json` and the stricter runtime parser in `promptbranch_application_architecture.py`.

Every Promptbranch runtime application or PB domain module must declare:

1. instructions and policy;
2. runtime agents or controlled reasoning actors;
3. versioned skills;
4. bounded tools;
5. fail-closed validators;
6. authoritative knowledge and project context;
7. typed state and contracts;
8. evidence and execution records;
9. controller and authority boundaries;
10. lifecycle integration and recovery.

The declaration has one sole version authority, uses repository-relative paths without traversal, and must not self-grant mutation, release, publication, or adoption authority. Promptbranch runtime applications own generic execution capabilities. Domain modules must delegate those capabilities explicitly and own only their domain behavior.

PBAI-001 registry validation and reference resolution remain read-only. Architecture validation is read-only through registry proof. Executable proof requires an explicit `--level executable` or `architecture evidence` request and may run only the sole tracked proof skill through MCP stdio. `v0.1.114` implements declaration, structural, registry, and executable validation. The executable contract must declare exact ordered read-only tools, validators, an evidence contract, maximum steps, and timeout. Every SkillRun must validate its per-step digests and canonical evidence hash. Repository, Project Source, release, publication, and adoption state must remain unchanged. Before `v0.1.115`, operational proof remained fail-closed and unimplemented.

## v0.1.114.2 deterministic candidate test-runner policy

Strict release validation must execute the freshly installed pipx candidate, not an ambient virtual environment earlier on `PATH`. The candidate package must include `pytest==9.0.2`; release control must verify its distribution version, module path, and interpreter prefix inside the exact candidate venv before Project Source mutation. Every release-validation command must use the absolute candidate Python through `PROMPTBRANCH_RELEASE_VALIDATION_PYTHON`; the venv launcher path must not be symlink-resolved to the base interpreter. FastAPI `0.128.2` and Starlette `0.50.0` remain the tested compatibility pair. This repair is scope-neutral and must not change PBAI executable or SkillRun authority.

## v0.1.115 PBAI operational and fast-test policy

`v0.1.115` implements the PBAI-001 operational proof boundary. Operational proof is post-adoption and may be claimed only from a tamper-evident lifecycle evidence record that verifies strict 10/10 validation, Project Source publication identity, evidence-bound adoption, accepted/current identity, rollback, recovery, and Artifact Guardian. The evidence builder and validator are read-only and may not perform publication, adoption, state mutation, or Git operations.

Development testing uses `pb test impacted`. Its checked-in map must select tests from changed repository paths, close transitive dependencies, explain each selection, and fail closed for unmapped paths. Edit, component, and candidate modes are development evidence only. Exact-key reuse requires matching version, Git base/head revisions, changed-file content hashes, selected command definitions, test-definition hashes, interpreter identity, dependency versions, platform identity, selected groups, and map hash. No impacted-test result can replace the strict release/adoption gate.
