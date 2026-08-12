# Promptbranch overview

Promptbranch (PB) is a deterministic control plane for coordinating an AI-assisted workflow across a local repository, ChatGPT Project/conversation state, browser-backed operations, artifacts, validation, and release/adoption evidence.

The key idea is separation of concerns:

- **AI reasoning proposes and explains.**
- **PB deterministic code resolves identity, policy, state and evidence.**
- **Write-capable operations require explicit authority and independent verification.**
- **Artifacts are immutable by SHA; accepted/current is a project-scoped authority decision, not a filename convention.**

## Canonical mental model

A normal PB workflow moves through explicit layers:

1. **Repository** — source, schemas, skills, tests and project-control documents.
2. **Workspace / Project** — the active ChatGPT Project identity and PB workspace state.
3. **Task / Conversation** — a correlated conversation or task-message context.
4. **Skill / Tool** — bounded procedure and deterministic tool contracts.
5. **Execution** — browser/service/MCP/CLI mechanisms that may observe or mutate state according to policy.
6. **Evidence** — machine-readable proof of what happened.
7. **Artifact** — deterministic immutable release ZIP identified by SHA-256.
8. **Lifecycle** — candidate, tested, accepted, adopted/current and final verification.
9. **Application boundary** — PB controls the workflow; an external application's own repository/runtime remains separate authority.

## What PB is not

PB is not an LLM prompt that treats natural-language intent as authority. It is not a collection of aliases for historical command paths. It is not a best-effort browser macro where a visible success-looking string is accepted without causality. It is not a release process where rebuilding the same version silently creates a new authoritative artifact.

## First principles

- deterministic where authority matters;
- fail closed on ambiguity;
- one canonical current mechanism;
- explicit identities;
- smallest required mutation;
- evidence before claims;
- independently verified state transitions;
- no hidden compatibility path for superseded PB internals unless a current external contract requires one.
