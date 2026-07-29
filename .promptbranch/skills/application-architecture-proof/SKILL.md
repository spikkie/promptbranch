---
name: application-architecture-proof
description: Execute the bounded PBAI-001 proof using repository-local read-only MCP tools.
risk: read
allowed_tools:
  - filesystem.read
  - filesystem.list
prechecks:
  - repo_path_exists
  - architecture_declaration_exists
  - tool_read_only
---

## Procedure

1. Read the tracked `.promptbranch-ai.json` declaration.
2. List the tracked `.promptbranch` control directory.
3. Return only bounded read-only evidence; never mutate repository, Project Source, release, publication, or adoption state.
