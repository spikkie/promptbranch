# Promptbranch MVP Plan — MCP Client/Server, Ollama, Agents, and Skills

Created: 2026-05-03

## Goal

Build a Promptbranch-native local agent architecture.

Not:

```text
Cursor/Claude Desktop host → Promptbranch server
```

But:

```text
Promptbranch host → Promptbranch MCP client → Promptbranch MCP server
```

with optional Ollama proposal/summarization and local skills.

## MVP principle

Every new layer must be independently testable:

```text
MCP server works without Ollama.
MCP client works without Ollama.
Agent works without ChatGPT/browser.
Skill validation works before skill execution.
Ollama proposal can fail without breaking deterministic tool calls.
```

## MVP phases

### Phase 1 — Native MCP host/client loop

Implement/standardize:

```bash
pb agent host-smoke --path . --json
pb agent mcp-call filesystem.read '{"path":"VERSION"}' --path . --json
pb agent run "read VERSION and git status" --path . --json
```

Expected behavior:

```text
pb agent run
  → deterministic planner
  → Promptbranch MCP client
  → pb mcp serve over stdio
  → filesystem.read + git.status
  → structured result
```

Acceptance criteria:

- Uses actual stdio JSON-RPC boundary.
- Does not call ChatGPT/browser.
- Does not require Cursor/Claude Desktop.
- Rejects write tools.
- Logs request, plan, tool calls, MCP transport, result, and policy decision.

### Phase 2 — Skill registry

Implement:

```bash
pb skill list --json
pb skill show repo-inspection --json
pb skill validate .promptbranch/skills/repo-inspection --json
pb agent run --skill repo-inspection "inspect repo" --path . --json
```

Create built-in skill:

```text
repo-inspection
```

Skill procedure:

1. read `VERSION` if present
2. run `git.status`
3. if dirty, run `git.diff.summary`
4. report version, branch, short SHA, dirty state, and risk

Acceptance criteria:

- Skill must have `SKILL.md`.
- Skill must declare `allowed_tools`.
- Unknown tools are rejected.
- Write tools are rejected unless skill risk and command mode explicitly allow them.
- Local skills only in MVP.

### Phase 3 — Ollama proposal and summary

Implement:

```bash
pb agent ollama-propose "read VERSION" --model llama3.2:3b --json
pb agent run "read VERSION" --model llama3.2:3b --path . --json
pb agent summarize-log <file> --model llama3.2:3b --json
```

Acceptance criteria:

- Model output must be parsed strictly.
- Invalid output must fail closed.
- Model proposals must go through same policy gate.
- Model summary failure must not hide raw tool results.
- Model is never allowed to execute directly.

### Phase 4 — Controlled test execution

Implement:

```bash
pb agent tool-call test.smoke '{}' --path . --json
pb agent run "run smoke tests" --path . --json
```

Acceptance criteria:

- timeout required
- stdout/stderr captured
- exit code captured
- no cleanup/destructive actions
- no ChatGPT project mutation
- no arbitrary shell command input yet

### Phase 5 — Controlled source/artifact writes

Implement only after Phases 1–4 are stable:

```bash
pb src sync . --json
pb artifact verify <zip> --json
pb artifact release --json
```

Acceptance criteria:

- before/after state snapshots
- collateral-change detection
- transactional verification
- state update only after verification
- baseline continuity enforced
- ZIP opens directly to repo contents, no wrapper folder

## Current non-goals

- broad shell execution
- autonomous repo editing
- autonomous project source overwrite
- autonomous release packaging
- remote skill download
- remote skills-over-MCP
- Cursor/Claude Desktop dependency
- HTTP MCP transport

## Recommended next release scope

Next release should be narrow:

```text
Add `pb agent run` as the canonical Promptbranch-native host command.
Add `pb skill list/show/validate`.
Add built-in repo-inspection skill.
Keep everything read-only.
```

## Test plan

Run:

```bash
pbv

pb agent host-smoke --path . --json   2>&1 | tee pb_agent_host_smoke.<version>.log

pb agent run "read VERSION and git status" --path . --json   2>&1 | tee pb_agent_run_readonly.<version>.log

pb skill list --json   2>&1 | tee pb_skill_list.<version>.log

pb skill validate .promptbranch/skills/repo-inspection --json   2>&1 | tee pb_skill_validate_repo_inspection.<version>.log

pb agent run --skill repo-inspection "inspect repo" --path . --json   2>&1 | tee pb_agent_run_skill_repo_inspection.<version>.log
```

## Decision rules

If Ollama output is invalid:

```text
do not execute model proposal
return model_tool_call_invalid
preserve raw deterministic results where applicable
```

If skill is invalid:

```text
do not run agent
return skill_invalid
show invalid field/tool/precheck
```

If MCP server cannot start:

```text
return mcp_transport_unavailable
do not fall back silently to internal dispatcher
```

If write tool is requested:

```text
reject by default
return write_tool_blocked
```

## Verdict

The MVP should prove a constrained, reproducible, local loop:

```text
Promptbranch host
  → MCP client
  → MCP server
  → read-only tools
  → optional skill guidance
  → optional Ollama explanation
```

This is the right foundation before any write-capable or release-generating agent behavior.
