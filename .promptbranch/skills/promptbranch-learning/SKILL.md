---
name: promptbranch-learning
description: Learn Promptbranch end-to-end through one canonical, audience-neutral curriculum without gaining execution authority.
risk: read
allowed_tools:
  - filesystem.read
  - filesystem.list
prechecks:
  - repo_path_exists
  - tool_read_only
---

# Promptbranch Learning

Use this skill when a human, ChatGPT, Claude/coding agent, or another PB-aware agent needs to learn Promptbranch itself rather than one isolated command or subsystem.

## Canonical learning order

1. Read `PROMPTBRANCH_OVERVIEW.md` for the mental model and vocabulary.
2. Read `AUTHORITY_MODEL.md` before following any operational example.
3. Read `LEARNING_PATH.md` and choose the human, ChatGPT Project, coding-agent, or PB-aware-agent track.
4. Read `QUICKSTART.md` to inspect a PB environment using read-only commands first.
5. Read `OPERATOR_GUIDE.md` before performing stateful PB operations.
6. Read `DEVELOPER_GUIDE.md` before extending skills, tools, schemas, validators, release logic, or application workflows.
7. Complete `EXERCISES.md`; every exercise has an expected evidence/verdict contract.
8. Use `GLOSSARY.md` to resolve Promptbranch-specific terminology.
9. Use the embedded related skills when the learning path reaches repo inspection, final-MVP inspection, application-architecture proof, or tool authoring.

## Learning invariants

- Distinguish observation, planning, execution, publication, acceptance, adoption, and authoritative current.
- Treat the project/repository/artifact/conversation identities as explicit state, never as implicit context.
- Read-only learning material does not grant execution authority.
- A valid skill or tool specification does not authorize mutation.
- Unknown, ambiguous, stale, or contradictory authority state fails closed.
- Prefer the current canonical mechanism; do not learn superseded PB internals as alternative supported paths.
- Evidence must bind the operation, identity, result, and verdict.

## Completion criterion

A learner is ready to operate Promptbranch only when they can explain the authority model, identify accepted/current state, distinguish Project Sources from artifact authority, classify read/write/destructive operations, and complete the read-only exercises without relying on undocumented tribal knowledge.

## Authority boundary

This skill teaches and inspects. It grants no repository mutation, browser mutation, Project Source mutation, external process execution, release, publication, acceptance, adoption, or deployment authority.
