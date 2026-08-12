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

## Backlog handling

Read `docs/backlog/backlog.json` before implementing planned ticket work. Do not treat historical DoD entries or release-horizon slices as open tickets unless they are explicitly registered there. Follow `implementation_order` and declared dependencies.

## PBAI-001 architecture work

Before changing AI application behavior, read `.promptbranch-ai.json` after `PROJECT_SETTINGS.md` and before implementation-specific code. Treat its version authority, ten architecture layers, delegation contract, authority boundaries, and validation commands as tracked input, not as permission to execute or mutate.

Required agent behavior:

- run `pb application architecture plan --repo-path . --json` for a read-only declaration plan;
- run `pb application architecture validate --repo-path . --level structural --json` and `pb application architecture validate --repo-path . --level registry --json` before packaging;
- fail closed on unknown fields, missing or empty layers, absolute paths, traversal, repeated cross-layer ownership, unsafe commands, delegation conflicts, or self-granted authority;
- never execute project-local validation commands merely because they are declared;
- read `.promptbranch/ai-registry.json`; fail closed on missing, duplicate, ambiguous, mismatched, or unbounded references;
- execute architecture proof only after an explicit executable/evidence request, only through the sole tracked proof skill, only with its exact registered read-only tool order and bounds;
- validate the complete `promptbranch.ai.skill_run` record, per-step digests, run identity, and canonical evidence hash before reporting `proven_level=executable`;
- never infer operational proof, mutation authority, Project Source authority, release authority, publication authority, or adoption authority from executable evidence;
- keep domain modules dependent on Promptbranch generic runtime capabilities rather than duplicating them;
- record explicit migration requirements for repositories without a declaration instead of adding silent fallback behavior.

## Candidate runtime repair work

For candidate installation and release validation:

- never trust ambient `pb`, `promptbranch`, or Python resolution after pipx installation;
- derive and verify the exact candidate pipx venv executables;
- fail closed when PATH shadowing or interpreter-prefix drift is observed;
- run import-smoke with the exact candidate Python and require FastAPI/Starlette version parity with the tracked dependency contract;
- preserve all PBAI structural, registry, executable, SkillRun, publication, adoption, and accepted/current gates;
- do not advance to the next normal slice until the active repair candidate passes strict host validation and adoption.

## PBAI-001 template, migration, and differential-validation operator contract

Use `pb application architecture template` as a deterministic plan; repository writes require explicit `--write`. Use `migration-report` for read-only gap analysis. Keep project-local validators until `differential-validate` proves Promptbranch equivalent or stronger on identical isolated cases. A domain module may report only its highest actual proof level and may not self-grant mutation, publication, release, or adoption authority.


## Release-set planner rules

- Treat `pb release set plan` as a read-only operation.
- Require the manifest project id to match the tracked `.promptbranch-repo.json` project binding.
- Resolve a dependency from another release-set target when present; otherwise use only accepted/current project-registry evidence.
- Never infer missing versions, repositories, artifacts, hashes, or compatibility constraints.
- Reject cycles, unsupported constraint grammar, path traversal, noncanonical artifact names, ZIP failures, VERSION mismatch, and SHA-256 mismatch.
- Do not execute, publish, adopt, modify registries, mutate Project Sources, or create rollback evidence from the planner.

## Release-set rollout operating rules

- Treat `pb release set plan` and `pb release set evidence-validate` as read-only operations.
- Never run `pb release set apply` without exact plan digest confirmation and every required lifecycle authorization flag.
- Require rollback-on-failure for every release-set mutation.
- Stop on the first failed repository and roll back only repositories proven completed, in reverse completion order.
- Never claim recovery unless the exact previous artifact SHA and Project Source identities are independently verified.
- Preserve rollout checkpoints and hash-chain evidence; do not rewrite or normalize completed evidence files.

## Release-set recovery operating rules

- Run `pb release set reconcile` before every interrupted rollout or rollback recovery attempt.
- Treat reconciliation as read-only and preserve the emitted checkpoint SHA-256, original plan SHA-256, repository classifications, recovery mode, and reconciliation SHA-256.
- Do not run `pb release set resume` unless all exact confirmation fields and lifecycle authorization flags are present.
- Never replay a repository already proven at its exact target identity.
- Continue forward execution only from repositories proven at their exact pre-rollout identity.
- Resume rollback only for repositories still proven at the exact target identity and follow reverse dependency order.
- Do not invent an operator resolution for `missing_current` or `ambiguous_current`; report the blocker and require explicit external repair followed by a fresh reconciliation.
- Preserve the original event chain and append resume history; never discard or silently rewrite prior checkpoint evidence.

## Promptbranch learning/onboarding

When the task is to learn Promptbranch itself, start with `.promptbranch/skills/promptbranch-learning/SKILL.md` and its canonical learning path before reconstructing behavior from historical release notes. Use `.promptbranch/skills/promptbranch-operator/SKILL.md` for operator reasoning and `.promptbranch/skills/promptbranch-tool-authoring/SKILL.md` for deterministic tool design. Learning and skill validation do not grant mutation authority.
