---
name: promptbranch-tool-authoring
description: Author deterministic Promptbranch tool specifications without granting execution authority.
risk: read
allowed_tools:
  - filesystem.read
  - filesystem.list
prechecks:
  - repo_path_exists
  - tool_read_only
---

# Promptbranch Tool Authoring

Use this skill to design a tool contract that Promptbranch can review, validate, register, and later execute only through a separately authorized control-plane path. **Authoring is proposal-only. It never grants execution, mutation, release, publication, or adoption authority.**

## Deterministic tool contract

Every authored tool specification MUST conform to `promptbranch.tool.authoring` schema `1.0` and MUST contain these explicit domains:

1. **Identity** — stable `id`, non-empty `description`, and explicit `provider`.
2. **Input schema** — JSON object input with declared properties and `additionalProperties: false`. Never accept an unbounded free-form argument bag.
3. **Risk** — one of `read`, `external_process`, `write`, or `destructive`, plus an explicit `read_only` boolean. `risk: read` requires `read_only: true`; every other risk requires `read_only: false`.
4. **Authority** — registration is `proposal_only`; execution, mutation, release, publication, and adoption MUST all remain `not_granted` in an authoring specification.
5. **Validation** — deterministic preconditions and at least one named validator. Validation failure blocks registration or later execution; it is not advisory.
6. **Evidence** — evidence is mandatory, names its contract, and declares the minimum fields required to bind arguments, result, and verdict.
7. **Failure semantics** — `mode: fail_closed` with stable machine-readable failure codes. Unknown, ambiguous, or malformed input is a failure, not a fallback trigger.

## Procedure

1. Inspect the existing registry, MCP tool manifest, and relevant schemas using read-only tools only.
2. Choose one stable tool id and one provider. Do not create aliases or compatibility names for superseded Promptbranch internals.
3. Define the smallest JSON input schema that can express the operation. Reject undeclared fields.
4. Classify risk from the real side effects, not from the requested name or intended use.
5. Keep all authoring authority fields non-executable. If the proposed tool would eventually mutate anything, record that risk but do not grant mutation authority here.
6. Define deterministic preconditions and validators that can independently reject unsafe or ambiguous state.
7. Define evidence fields sufficient to prove what input was accepted, what result occurred, and which validator produced the verdict.
8. Define stable failure codes for invalid arguments, unavailable authority, validation failure, ambiguous state, and provider failure as applicable.
9. Validate the specification before proposing registry changes.
10. Treat registry editing, implementation, execution, publication, and adoption as separate operator-authorized work.

## Portable export surfaces

A canonical Promptbranch export bundle contains:

- `SKILL.md` — this procedure;
- `TOOL_SPEC.schema.json` — the deterministic machine-readable authoring schema;
- `examples/read-version.tool.json` — a minimal valid example;
- `PROJECT_SOURCE.md` — a self-contained ChatGPT Project Source rendering;
- `AGENTS.md` — coding-agent instructions preserving the same authority boundary;
- `manifest.json` — version, file digests, deterministic ZIP contract, and explicit false authority grants.

The bundle is deterministic: entries are sorted, timestamps and file modes are fixed, and the manifest contains SHA-256 for every payload file. Bundle verification MUST reject missing, extra, modified, or authority-escalating content.

## Failure rules

- Missing or malformed schema: fail closed.
- Unknown top-level fields: fail closed.
- Unbounded input (`additionalProperties` not exactly `false`): fail closed.
- Read-risk/read-only mismatch: fail closed.
- Any authoring authority that grants execution or mutation: fail closed.
- Missing validators, evidence contract, evidence fields, or failure codes: fail closed.
- Export bundle digest mismatch, extra entry, unsafe path, or manifest authority escalation: fail closed.

## Authority boundary

This skill can help **author and inspect** tool specifications. It does not register a tool, execute a tool, edit repository state, mutate a ChatGPT Project Source, publish a release, adopt an artifact, or authorize a destructive operation. Those are separate Promptbranch control-plane transitions and remain fail-closed.
