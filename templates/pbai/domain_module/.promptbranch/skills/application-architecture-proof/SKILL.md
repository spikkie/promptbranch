---
name: application-architecture-proof
description: Execute the bounded PBAI-001 proof for example-domain using repository-local read-only tools.
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
2. List the tracked `.promptbranch` AI control directory.
3. Return bounded read-only evidence only; never mutate repository, publication, release, or adoption state.
