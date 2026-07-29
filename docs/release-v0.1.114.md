# v0.1.114 — PBAI-001 executable validation and SkillRun evidence

## Scope

This candidate advances Promptbranch's PBAI-001 proof from `registry` to `executable` without claiming operational lifecycle proof.

## Added

- Declaration schema `1.2` and registry schema `1.1`.
- Portable `application-architecture-proof` skill.
- Exact executable contract: request, ordered tools, validators, evidence contract, maximum steps, and timeout.
- Real MCP stdio skill execution.
- `promptbranch.ai.skill_run` evidence schema and validator.
- Per-step argument and result SHA-256 digests.
- Canonical evidence hash and run identity.
- `pb application architecture evidence --json`.
- Required `application_architecture_executable` release-validation group.

## Safety

The proof uses only `filesystem.read` and `filesystem.list`. It performs no repository mutation, Project Source mutation, release, publication, adoption, or accepted/current update. Operational proof remains unimplemented and fails closed.
