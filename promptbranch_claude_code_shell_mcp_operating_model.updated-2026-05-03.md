# Promptbranch as a Claude-Code-like Shell with MCP, Ollama, Agents, and Skills

Updated: 2026-05-03

## Purpose

Promptbranch should become a constrained Claude-Code-like development workflow shell around ChatGPT Projects.

The practical target is:

```text
Promptbranch is the local control plane.
ChatGPT.com is the project/task execution surface.
MCP provides deterministic local tools.
Ollama provides optional local reasoning/summarization.
Skills provide reusable operating procedures.
```

Do not make Cursor, Claude Desktop, or any external host a dependency. Promptbranch should implement its own host/client architecture.

---

## 1. Current object model

Promptbranch has three active scopes:

```text
Workspace = current ChatGPT Project
Task      = current Chat / conversation inside the project
Artifact  = current source bundle, repo snapshot, or release ZIP
```

A task contains conversation content:

```text
Task / Chat
  Turn[]
    user_message
    assistant_answers[]
```

Do not hard-code one answer per message. A turn may have no answer after timeout, one answer, or multiple answers later.

---

## 2. Current implementation state

### 2.1 Shell grammar

Canonical grammar:

```bash
pb ws ...
pb task ...
pb src ...
pb artifact ...
pb test ...
pb debug ...
pb doctor
pb ask ...
pb agent ...
pb mcp ...
pb skill ...
```

Implemented or partially implemented:

```bash
pb ws list/use/current/leave
pb task list/use/current/leave/show
pb task messages list
pb task message show
pb task message answer
pb src list/add/rm
pb ask
pb test smoke
pb doctor
pb mcp manifest
pb mcp serve
pb mcp config
pb mcp host-smoke
pb agent ask
pb agent tool-call
pb agent models
pb agent mcp-llm-smoke
```

Legacy aliases may remain but should not be the primary grammar.

### 2.2 MCP server

Promptbranch currently exposes a read-only MCP-style server:

```bash
pb mcp serve --path .
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

Default MCP mode:

```text
read_only
```

Controlled writes can be listed only when explicitly requested, but execution must remain blocked until safe write execution is implemented.

### 2.3 MCP host/client

We will build our own Promptbranch-native host/client.

Architecture:

```text
pb agent run / pb agent host
  ├─ MCP client manager
  ├─ policy-gated executor
  ├─ skill registry
  ├─ optional Ollama adapter
  └─ MCP server subprocesses
       └─ pb mcp serve --path <repo>
```

Current tested call paths:

```bash
pb agent ask "read VERSION and git status" --path . --json
```

This uses deterministic rule-based planning and read-only tools.

```bash
pb agent mcp-llm-smoke "read VERSION" --path . --model llama3.2:3b --json
```

This asks Ollama to propose one MCP call, then Promptbranch validates and executes it through MCP stdio only if safe.

### 2.4 Ollama

Ollama is available locally, but current model output is not reliable enough for planning.

Observed:

- `qwen2.5-coder:3b` failed JSON-only planning by emitting unrelated repeated code.
- `llama3.2:3b` returned `{}` or invalid/repetitive JSON-like content under JSON mode.

Policy:

```text
Ollama must not be the default executor.
Ollama must not update state.
Ollama must not choose baselines.
Ollama must not call write tools.
Ollama may propose one structured tool call only.
Promptbranch validates every proposal.
Invalid output fails closed.
```

Use cases allowed now:

```text
- summarize logs
- explain read-only tool results
- propose one read-only tool call for smoke testing
```

### 2.5 Skills

Skills are workflow/instruction packages, not MCP servers.

Skill responsibilities:

```text
- describe repeatable workflows
- list allowed tools
- define preconditions
- define expected outputs
- document failure handling
```

Skill non-responsibilities:

```text
- execute commands directly
- bypass policy gates
- approve destructive actions
- select release baselines alone
```

Recommended local registry:

```text
.promptbranch/skills/
  repo-inspection/
    SKILL.md
    references/
  source-sync/
    SKILL.md
    references/
```

Recommended global registry:

```text
~/.config/promptbranch/skills/
```

---

## 3. Updated architecture

### 3.1 Runtime stack

```text
User
  ↓
Promptbranch CLI
  ↓
Promptbranch local host
  ├─ deterministic planner
  ├─ skill-guided planner
  ├─ policy gate
  ├─ Ollama proposal/summarization adapter
  ├─ MCP client manager
  └─ MCP servers
       ├─ Promptbranch MCP server
       ├─ filesystem/git/artifact tools
       └─ future controlled test/artifact servers
```

### 3.2 Data flow: deterministic read-only agent

```text
User asks: "read VERSION and git status"
  ↓
Rule-based planner
  ↓
Policy validates read-only tools
  ↓
MCP tool calls:
  - filesystem.read VERSION
  - git.status
  ↓
Structured JSON result
```

### 3.3 Data flow: Ollama-proposed MCP smoke

```text
User asks: "read VERSION"
  ↓
Ollama proposes JSON:
  {"tool":"filesystem.read","arguments":{"path":"VERSION"}}
  ↓
Promptbranch validates:
  - valid JSON
  - known tool
  - read-only
  - arguments safe
  - repo-bound path
  ↓
Promptbranch MCP client calls pb mcp serve over stdio
  ↓
Structured JSON result
```

### 3.4 Data flow: skill-guided plan

```text
User asks: "inspect this repo"
  ↓
Skill registry selects repo-inspection
  ↓
Skill declares allowed tools:
  - filesystem.read
  - git.status
  - git.diff.summary
  ↓
Planner proposes calls
  ↓
Policy validates
  ↓
MCP executes
  ↓
Report generated
```

---

## 4. Security and safety model

### 4.1 Risk levels

```text
read       = safe automatic execution
process    = controlled execution, no filesystem mutation expected but may be expensive
write      = changes local/project state
destructive = deletes/removes/overwrites
```

### 4.2 Current auto-allowed tools

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

### 4.3 Blocked until next phases

```text
src add
src rm
src sync
artifact release
artifact push
test full
shell execution
git write operations
project source overwrite
```

### 4.4 Policy-gated executor

A proposed action must include:

```json
{
  "intent": "inspect_repo",
  "risk": "read",
  "tools": [
    {
      "name": "filesystem.read",
      "arguments": {"path": "VERSION"}
    }
  ],
  "prechecks": [
    "repo_path_exists",
    "path_repo_bound",
    "tool_read_only"
  ]
}
```

Executor validates before any MCP call.

---

## 5. Skills design

### 5.1 Skill package

```text
skills/<name>/
  SKILL.md
  references/
  scripts/      # optional, disabled by default
```

### 5.2 Minimal skill schema

```markdown
---
name: repo-inspection
description: Inspect repository state using read-only MCP tools.
risk: read
allowed_tools:
  - filesystem.read
  - filesystem.list
  - git.status
  - git.diff.summary
prechecks:
  - repo_path_exists
  - tool_read_only
---

## Procedure

1. Read VERSION if present.
2. Read git.status.
3. If dirty, read git.diff.summary.
4. Report version, branch, short SHA, dirty state, and risk.
5. Never execute write tools.
```

### 5.3 Skill commands

MVP commands:

```bash
pb skill list --json
pb skill show repo-inspection --json
pb skill validate .promptbranch/skills/repo-inspection --json
pb agent run --skill repo-inspection "inspect repo" --path . --json
```

Later:

```bash
pb skill install <path-or-url>
pb skill sync <mcp-server>
pb skill export <name>
```

Do not implement remote skill install before local validation is solid.

---

## 6. Updated MVP plan

### MVP-A — stabilize Promptbranch-native MCP host/client

Goal: prove local host/client/server loop without external hosts.

Deliverables:

```bash
pb agent host-smoke --path . --json
pb agent mcp-call filesystem.read '{"path":"VERSION"}' --path . --json
pb agent run "read VERSION and git status" --path . --json
```

Acceptance:

- no ChatGPT/browser dependency
- no external MCP host dependency
- uses actual `pb mcp serve` stdio boundary
- rejects write tools
- logs model proposal separately from executed tool call

### MVP-B — add local skills registry

Goal: skills guide read-only planning.

Deliverables:

```bash
pb skill list --json
pb skill show repo-inspection --json
pb skill validate .promptbranch/skills/repo-inspection --json
pb agent run --skill repo-inspection "inspect repo" --path . --json
```

Acceptance:

- local skills only
- no remote downloads
- `allowed_tools` enforced
- invalid skill rejected
- skill cannot grant write permission

### MVP-C — Ollama as optional proposal/summarizer

Goal: model can help but cannot break execution.

Deliverables:

```bash
pb agent ollama-propose "read VERSION" --model llama3.2:3b --json
pb agent run "read VERSION" --path . --model llama3.2:3b --json
pb agent summarize-log <file> --model llama3.2:3b --json
```

Acceptance:

- invalid model output fails closed
- raw tool results still returned
- model not used for write actions
- model output never mutates state

### MVP-D — controlled process tools

Goal: allow test execution under constraints.

Deliverables:

```bash
pb agent run "run smoke tests" --path . --json
pb agent tool-call test.smoke '{}' --path . --json
```

Acceptance:

- only smoke tests initially
- timeout required
- captured stdout/stderr
- no destructive cleanup unless explicitly allowed
- no project/source mutation

### MVP-E — source/artifact controlled writes

Goal: support useful workflow mutation safely.

Deliverables:

```bash
pb src sync . --json
pb artifact verify <zip> --json
pb artifact release --json
```

Acceptance:

- transactional writes
- before/after snapshots
- collateral-change detection
- state update only after verification
- explicit artifact baseline continuity

---

## 7. Non-goals for MVP

Do not implement yet:

```text
- broad shell execution
- autonomous source overwrite
- autonomous artifact release
- remote skill downloads
- write-capable MCP from Ollama proposal
- Cursor/Claude Desktop dependency
- HTTP MCP unless stdio host/client loop is stable
```

---

## 8. Recommended next implementation

The next release should implement **MVP-A + start MVP-B**, not write tools.

Recommended next version scope:

```bash
pb agent host-smoke --path . --json
pb agent run "read VERSION and git status" --path . --json
pb skill list --json
pb skill validate <path> --json
pb skill show repo-inspection --json
```

Do not add source sync or artifact release through the agent yet.

---

## 9. Verdict

### Strengths

- Promptbranch now has a real path to become its own MCP host/client.
- Read-only MCP tools are already usable.
- Skills fit naturally as reusable operating procedures.
- Ollama can remain useful without being trusted.

### Weaknesses

- Local LLM planning is not reliable yet.
- Write execution is still blocked and must remain blocked.
- Skills require validation or they become another source of hidden policy drift.

### Unknowns

- Whether a future local model can reliably emit structured tool calls.
- Whether skills-over-MCP becomes stable enough to consume remotely.
- Whether stdio remains sufficient or Streamable HTTP is needed later.

### Next step

Implement a Promptbranch-native local host/client loop and a local skill registry:

```bash
pb agent run "read VERSION and git status" --path . --json
pb skill list --json
pb skill validate .promptbranch/skills/repo-inspection --json
pb agent run --skill repo-inspection "inspect repo" --path . --json
```
