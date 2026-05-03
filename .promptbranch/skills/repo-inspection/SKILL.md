---
name: repo-inspection
description: Inspect repository state using read-only MCP tools.
risk: read
allowed_tools:
  - filesystem.read
  - git.status
  - git.diff.summary
prechecks:
  - repo_path_exists
  - tool_read_only
---

## Procedure

1. Read VERSION if present.
2. Run git.status.
3. If dirty, run git.diff.summary.
4. Report version, branch, short SHA, dirty state, and risk.
5. Never execute write tools.
