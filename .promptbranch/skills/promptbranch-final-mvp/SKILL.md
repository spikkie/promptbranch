---
name: promptbranch-final-mvp
description: Inspect the Promptbranch final MVP contract and current read-only state so external tools can decide the next safe operator step.
risk: read
allowed_tools:
  - filesystem.read
  - git.status
  - git.diff.summary
  - artifact.registry.current
prechecks:
  - repo_path_exists
  - tool_read_only
---

## Purpose

Expose the final Promptbranch MVP control-plane contract as a reusable, read-only skill for other tools.

## Procedure

1. Read VERSION.
2. Read docs/mvp-definition-of-done.md.
3. Read docs/promptbranch_mvp_current_state_and_plan_2026-05-24.md when present.
4. Read the current artifact registry entry.
5. Run git.status and git.diff.summary.
6. Report final MVP boundary visibility, accepted baseline visibility, working-tree state, and safe next operator actions.
7. Never download, migrate, adopt, source-sync, run release-control scripts, commit, push, or mutate project state.

## Contract for tool consumers

Treat this skill output as inspection and planning input only. A green report means the final MVP contract is visible and the local state is internally inspectable; it is not final adoption proof and it does not authorize write-capable automation.
