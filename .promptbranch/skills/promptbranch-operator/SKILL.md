---
name: promptbranch-operator
description: Operate Promptbranch from the canonical authority model using read-first, fail-closed procedures and explicit operator authorization.
risk: read
allowed_tools:
  - filesystem.read
  - filesystem.list
  - git.status
  - git.diff.summary
  - artifact.registry.current
prechecks:
  - repo_path_exists
  - tool_read_only
---

# Promptbranch Operator

Use this skill after the `promptbranch-learning` curriculum has established the Promptbranch mental and authority models.

## Procedure

1. Resolve repository identity and `VERSION`.
2. Inspect workspace/task state and authoritative artifact current before proposing mutation.
3. Inspect git status/diff when repository state matters.
4. Classify the requested operation as read, controlled external process, write, or destructive.
5. Verify all operation-specific preconditions before any separately authorized execution path is invoked.
6. Bind evidence to the exact repo/project/version/artifact/conversation identities involved.
7. After mutation, independently verify the intended state transition and check for collateral changes.
8. For release work, do not call a release accepted/current until adoption plus fresh authoritative-current verification converge on the same immutable artifact SHA.
9. On ambiguity, stale state, route mismatch, timeout without evidence, or authority disagreement: stop and fail closed.

## Operator learning surfaces

Read `OPERATOR_RUNBOOK.md`, `SAFE_INSPECTION.md`, and `FAILURE_CLASSIFICATION.md` from the portable bundle. Use the repository's canonical how-to documents for command-specific detail.

## Authority boundary

This tracked skill itself remains read-only. It can teach, inspect, classify, and propose the next safe operator action. Any write, destructive action, browser mutation, publication, release transition, acceptance, adoption, deployment, Git commit, or Git push requires the separate deterministic PB control-plane path and the required operator authority.
