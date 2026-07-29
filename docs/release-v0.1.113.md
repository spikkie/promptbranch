# v0.1.113 — PBAI-001 registry validation and reference resolution

## Baseline

Accepted/current `v0.1.112`.

## Scope

- declaration schema `1.1` with explicit registry authority;
- `.promptbranch/ai-registry.json` and strict packaged schema;
- exact Agent/Skill/Tool/Validator/state/evidence/controller ID resolution;
- static Python symbol, Skill frontmatter, and MCP manifest verification;
- exact capability coverage and bounded authority resolution;
- read-only CLI registry proof and required release gate.

## Non-goals

No registered behavior is executed. No SkillRun evidence, operational proof, template migration, Project Source mutation, adoption, Git commit, or Git push is implied by local candidate validation.

## Acceptance

Source and clean-ZIP registry tests, control/authority/behavioural validation, compile and shell syntax, Artifact Guardian, direct and localhost transport independence, external-live gates, and exact adoption identity must all pass.
