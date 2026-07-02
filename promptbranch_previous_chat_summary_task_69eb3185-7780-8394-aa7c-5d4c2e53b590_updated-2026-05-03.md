# Promptbranch Claude-Code Shell — Updated Source Summary

Updated: 2026-05-03

## Purpose

This source updates the previous Promptbranch project summaries with the current MCP/Ollama/skills/agent direction.

Promptbranch should behave like a constrained Claude-Code-like workflow shell around ChatGPT Projects:

```text
Promptbranch CLI / local host = control plane
ChatGPT Project              = workspace
ChatGPT chat/conversation    = task/session
Project sources              = repo snapshots, specs, logs, release ZIPs
MCP servers                  = deterministic local tools
Ollama                       = optional local proposal/summarization
Skills                       = reusable workflow instructions
Generated ZIP artifacts      = release outputs
Test/doctor/debug artifacts  = regression and diagnosis layer
```

The target is still not literal Claude Code parity. The realistic target is workflow shape: select workspace, select task, sync context, ask, inspect results, package release, and validate.

---

## Current architecture decision

We will **build our own MCP host/client on the machine where Promptbranch runs**.

Do not depend on Cursor or Claude Desktop as MCP hosts.

Correct architecture:

```text
Promptbranch local host
  ├─ MCP client manager
  ├─ deterministic policy gate
  ├─ optional Ollama adapter
  ├─ local skill registry
  └─ one or more MCP server connections
       └─ pb mcp serve --path <repo>
```

Cursor/Claude Desktop may be used as compatibility references, not as architectural dependencies.

---

## Key terms

### MCP server

Executable/service exposing tools/resources/prompts.

Promptbranch server:

```bash
pb mcp serve --path .
```

### MCP client

Protocol connection manager used by the host to talk to one MCP server.

Promptbranch should own this client.

### MCP host

Application that coordinates user requests, model calls, policy, and MCP clients.

Promptbranch should become this host.

### Ollama

Local model runner.

Current role:

```text
proposal/summarization only
not trusted execution
not default planner
```

### Skill

Reusable workflow instruction package.

A skill tells the agent **how to use tools**, not what it may execute without validation.

---

## Implemented status through v0.0.143

### Read-only MCP server

Implemented:

```bash
pb mcp manifest --json
pb mcp serve --path .
pb mcp config --path . --json
pb mcp host-smoke --path . --json
```

Read-only tools:

```text
promptbranch.state.read
promptbranch.workspace.current
promptbranch.task.current
filesystem.list
filesystem.read
git.status
git.diff.summary
artifact.registry.current
artifact.verify
```

### Deterministic read-only agent

Implemented:

```bash
pb agent ask "read VERSION and git status" --path . --json
pb agent tool-call filesystem.read '{"path":"VERSION"}' --path . --json
pb agent models --json
```

Observed successful behavior:

```text
pb agent ask "read VERSION and git status"
  → filesystem.read VERSION
  → git.status
  → structured JSON output
```

Ollama was not used for planning or summary in that successful deterministic path.

### Ollama model testing

Observed:

- Ollama is installed and reachable.
- Models are listed by `pb agent models --json`.
- `qwen2.5-coder:3b` emitted unrelated repeated code for a JSON-only planning prompt.
- `llama3.2:3b` emitted `{}` or invalid repetitive JSON-like content for simple tool-call prompts.

Decision:

```text
Do not use Ollama as trusted planner.
Use deterministic planning by default.
Use Ollama only for optional proposal/summarization.
Reject invalid model output.
```

### First Ollama-proposed MCP smoke

Implemented:

```bash
pb agent mcp-llm-smoke "read VERSION" --path . --model llama3.2:3b --json
```

Purpose:

```text
Ollama proposes one tool call.
Promptbranch validates it.
Promptbranch calls actual MCP server over stdio if allowed.
```

This is a test path, not default execution.

---

## Skills update

Skills are now part of the planned architecture.

A skill is not an MCP server.

Use this model:

```text
MCP server = capability
Skill      = operating procedure
Host       = orchestration and policy
Ollama     = optional reasoning/summarization
```

Recommended skill package:

```text
.promptbranch/skills/repo-inspection/
  SKILL.md
  references/
```

Example:

```markdown
---
name: repo-inspection
description: Inspect repo state using read-only tools.
risk: read
allowed_tools:
  - filesystem.read
  - git.status
  - git.diff.summary
---

1. Read VERSION.
2. Read git.status.
3. If dirty, read git.diff.summary.
4. Report version, branch, short SHA, dirty state, and risk.
5. Never use write tools.
```

Skills must be validated:

```text
unknown tool → reject
write tool in read skill → reject
missing allowed_tools → reject
invalid frontmatter → reject
```

---

## Updated MVP plan

### MVP 1 — Promptbranch-native MCP host/client

Deliver:

```bash
pb agent host-smoke --path . --json
pb agent run "read VERSION and git status" --path . --json
pb agent mcp-call filesystem.read '{"path":"VERSION"}' --path . --json
```

Acceptance:

- uses actual `pb mcp serve` stdio boundary
- no external host dependency
- no ChatGPT/browser dependency
- read-only tools only
- rejects write tools

### MVP 2 — Local skill registry

Deliver:

```bash
pb skill list --json
pb skill show repo-inspection --json
pb skill validate .promptbranch/skills/repo-inspection --json
pb agent run --skill repo-inspection "inspect repo" --path . --json
```

Acceptance:

- local skills only
- `allowed_tools` enforced
- invalid skill rejected
- skill cannot grant write permission

### MVP 3 — Ollama proposal/summarization

Deliver:

```bash
pb agent ollama-propose "read VERSION" --model llama3.2:3b --json
pb agent summarize-log <file> --model llama3.2:3b --json
```

Acceptance:

- invalid model output fails closed
- model never mutates state
- model never executes write tools
- raw tool results are always available

### MVP 4 — Controlled process tools

Deliver:

```bash
pb agent tool-call test.smoke '{}' --path . --json
pb agent run "run smoke tests" --path . --json
```

Acceptance:

- timeout required
- stdout/stderr captured
- no destructive cleanup without explicit permission
- no source/project mutation

### MVP 5 — Controlled source/artifact writes

Deliver later:

```bash
pb src sync . --json
pb artifact verify <zip> --json
pb artifact release --json
```

Acceptance:

- transactional writes
- before/after snapshots
- collateral-change detection
- state update only after verified outcome
- release baseline continuity preserved

---

## Non-goals for the next MVP

Do not implement yet:

```text
- broad shell execution
- autonomous source overwrite
- autonomous artifact release
- remote skill downloads
- write-capable MCP execution from Ollama proposal
- Cursor/Claude Desktop dependency
- HTTP MCP transport before stdio host/client is stable
```

---

## Updated risk assessment

### Strong

- Workspace/Task/Artifact model.
- Backend-first and transactional write rules.
- Read-only MCP tool surface.
- Deterministic read-only `pb agent ask`.

### Weak

- Local LLM planning.
- Browser-driven project/source mutations.
- Write-capable MCP execution.
- Remote skill installation.

### Unknown

- Whether local models can become reliable structured planners.
- Whether skills-over-MCP stabilizes enough to consume remotely.
- Whether stdio remains sufficient or HTTP transport becomes useful.

---

## Recommended next release

Implement:

```bash
pb agent run "read VERSION and git status" --path . --json
pb agent host-smoke --path . --json
pb skill list --json
pb skill show repo-inspection --json
pb skill validate .promptbranch/skills/repo-inspection --json
pb agent run --skill repo-inspection "inspect repo" --path . --json
```

Keep all execution read-only.

---

## Verdict

Promptbranch should now move from “MCP server exists” to “Promptbranch is its own MCP host/client.”

The MVP is:

```text
Promptbranch owns orchestration.
MCP provides deterministic tools.
Skills guide workflow.
Ollama proposes or summarizes only.
Policy gate decides what actually executes.
```
