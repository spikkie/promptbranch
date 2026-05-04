# Promptbranch as a Claude-Code-like Shell with MCP/Ollama

## Purpose

Promptbranch should turn ChatGPT Projects into a Claude-Code-like development workflow shell.

The goal is not to make ChatGPT.com literally become Claude Code. ChatGPT Projects do not expose the same native repo/filesystem/edit/test loop that Claude Code has. The practical target is:

> Promptbranch is the local control plane. ChatGPT.com is the execution surface. MCP/Ollama provide local repo awareness, planning assistance, diagnostics, and deterministic tool access.

This document formalizes the model, current status, target workflow, and implementation plan.

---

## 1. Core object model

### 1.1 Shell/control-plane scopes

Promptbranch should persist only three active scopes:

- **Workspace** = current ChatGPT Project
- **Task** = current Chat / conversation inside the project
- **Artifact** = current source bundle, repo snapshot, or release ZIP

These map to a Claude-Code-like workflow without pretending ChatGPT is a filesystem.

### 1.2 Content model inside a task

A task contains conversation content:

- **Chat** has many **Messages**
- **Message** normally has one **Answer**

For implementation, do not hard-code exactly one answer. Use a safer internal model:

- **Task / Chat**
  - ordered **Turns**
    - one `user_message`
    - zero or more `assistant_answers`
    - optional status/metadata

Reason: a message may have no answer after timeout, may have partial output, or may later support retries/regenerations.

### 1.3 Recommended terminology

- **Project**: ChatGPT project container
- **Workspace**: Promptbranch's active project scope
- **Chat**: conversation thread inside a project
- **Task**: Promptbranch's active chat scope
- **Message**: user prompt within a task
- **Answer**: assistant response to a message
- **Turn**: implementation primitive containing message plus answer(s)
- **Artifact**: source ZIP, repo snapshot, release ZIP, or other versioned project source

---

## 2. Canonical shell grammar

Canonical commands should be grouped by domain:

```bash
pb ws ...
pb task ...
pb src ...
pb artifact ...
pb test ...
pb debug ...
pb doctor
pb ask ...
```

Short aliases may exist, but the documented and scriptable grammar should be the canonical form above.

### 2.1 Workspace commands

```bash
pb ws list
pb ws use <project>
pb ws current
pb ws leave
pb ws create <name>
pb ws ensure <name>
pb ws rm <project>
```

Purpose: manage the active ChatGPT Project.

### 2.2 Task commands

```bash
pb task list
pb task use <chat>
pb task current
pb task leave
pb task new [title]
pb task show
pb task summarize
pb task rename <title>
```

Purpose: manage the active chat/conversation inside the current workspace.

### 2.3 Message/answer commands

Messages and answers are subresources of a task, not top-level active scopes.

```bash
pb task messages list
pb task message show <id-or-index>
pb task message answer <id-or-index>
```

Possible later additions:

```bash
pb task message retry <id-or-index>
pb task message export <id-or-index>
```

### 2.4 Work execution

```bash
pb ask "..."
```

`pb ask` should append a message to the current task and capture the answer.

Avoid alias explosion unless behavior differs materially. `exec`, `continue`, and `reply` can be aliases later, but `ask` should remain the canonical execution verb.

### 2.5 Source commands

```bash
pb src list
pb src add --file <path>
pb src add --text <text-or-file>
pb src add --link <url>
pb src rm <source>
pb src sync <path>
pb src current
pb src pin <source>
```

Purpose: manage project sources/context.

Rules:

- File source names must use the basename only.
- Duplicate file adds should be idempotent.
- Mutations must be transactional and verified.
- Source replacement/sync must avoid collateral deletion.

### 2.6 Artifact commands

```bash
pb artifact list
pb artifact current
pb artifact use <version-or-file>
pb artifact release
pb artifact verify
```

Purpose: manage repo snapshots, release ZIPs, and baseline continuity.

Rules:

- Releases must be incremental from the latest accepted baseline.
- ZIPs must contain repo contents at the root, not a wrapper folder.
- Version stamping must be repo-wide.
- Stale version literals must be checked before packaging.

### 2.7 Reliability commands

```bash
pb doctor
pb test smoke
pb test full
pb test run --only <step>
pb test report
```

Purpose: detect breakage in project/chat/source/artifact flows before normal work depends on them.

### 2.8 Debug commands

```bash
pb debug project-list
pb debug chats
pb debug sources
pb debug save-flow
pb debug dump-state
pb debug artifacts
```

Debug commands should emit machine-readable artifacts every time.

---

## 3. Backend-first and transactional rules

### 3.1 Read operations

All reads should prefer stable structured data over UI scraping.

Preferred order:

1. backend JSON / network payload
2. saved Promptbranch state
3. DOM scraping
4. OCR/image fallback

Examples:

- workspace/project listing should prefer backend project payloads
- task/chat listing should prefer project-scoped backend conversation data
- source listing should prefer backend payloads if available, DOM fallback only if necessary

### 3.2 Write operations

All writes must be treated as transactions.

Required sequence:

1. trigger action
2. wait for settled/backend-confirmed state
3. re-read and verify persistence
4. update Promptbranch state only after verification

Never:

- assume success immediately after a click
- refresh before commit/save is stable
- update local state before persistence is confirmed
- retry destructive UI actions without detecting collateral changes

### 3.3 Mutation result schema

Every mutating operation should return structured status:

```json
{
  "ok": true,
  "action": "src_add",
  "requested": {},
  "triggered": true,
  "committed": true,
  "verified": true,
  "state_updated": true,
  "status": "verified"
}
```

Recommended statuses:

- `verified`
- `already_exists`
- `already_absent`
- `expected_skip`
- `expected_unsupported`
- `triggered_not_verified`
- `backend_mismatch`
- `rate_limited`
- `ui_changed`
- `collateral_change_detected`
- `timeout_unverified`

---

## 4. Current status

### 4.1 Implemented / partially implemented

#### Workspace / Project

Current status: mostly **CRD**, not full CRUD.

Implemented:

- project create
- project list/read
- project resolve/use
- project remove
- `.pb_profile` inherited workspace state

Missing:

- project update
- project rename
- update icon/color/memory mode after creation

#### Task / Chat

Current status: **read + local selection + implicit creation through ask**.

Implemented or partially implemented:

- chat list
- chat use
- chat show
- chat summarize
- ask in selected/current chat

Missing:

- canonical `pb task ...` grammar
- explicit task create
- task rename
- task delete/archive
- formal message/answer list model

#### Message / Answer

Current status: **implicit create/read only**.

Implemented:

- `pb ask` creates a new user prompt/turn
- `chat-show` can read conversation content

Missing:

- list messages in a task
- show one message by ID/index
- show answer for a specific message
- retry/regenerate model
- stable turn IDs/indexing

#### Sources / Artifacts

Current status: source **CRD**, artifact lifecycle partial/manual.

Implemented or partially implemented:

- source add
- source list
- source remove
- basename normalization for file path source adds
- duplicate-file add intended to be idempotent
- release ZIP generation in ChatGPT artifact workflow

Missing:

- canonical `pb src ...` grammar
- source sync from repo path
- source replace/update
- artifact current/use/list/release as first-class Promptbranch commands
- robust artifact baseline index

#### Reliability

Implemented or partially implemented:

- targeted test suites
- source-flow regressions
- `.pb_profile` state tests

Missing:

- canonical `pb doctor`
- canonical `pb test smoke`
- debug artifact commands
- daily smoke validation workflow as a first-class command

---

## 5. Claude Code process comparison

### 5.1 What Claude Code provides technically

Claude Code-like tools typically provide:

- local repo awareness
- file reading/editing
- shell command execution
- test execution
- task/session continuity
- codebase search
- diff generation
- commit/release assistance
- tool/hook integration

Promptbranch cannot directly duplicate the native local edit loop through ChatGPT Projects alone.

### 5.2 Promptbranch equivalent process

| Claude-Code-like capability | Promptbranch equivalent | Status |
|---|---|---|
| Open repo/worktree | `pb ws use <project>` + `.pb_profile` | mostly present |
| Start task/session | `pb task use/new` | partial |
| Ask coding question | `pb ask` | present |
| Continue task | selected task + `pb ask` | partial |
| Inspect session | `pb task show`, message list | partial |
| Understand codebase | project sources / repo ZIP / docs | present but brittle |
| Edit files | generated ZIP artifacts | manual/artifact-based |
| Run tests | local tests / `pb test smoke` | partial |
| Release | `pb artifact release` | not first-class yet |
| Debug automation | `pb debug ...` | not canonical yet |
| Guardrails | transactional writes + doctor/tests | partial |

### 5.3 Correct practical target

Do not target literal Claude Code parity.

Target same **process shape**:

```bash
pb ws use "project"
pb task new "fix bug"
pb src sync .
pb ask "analyze and patch"
pb artifact release
pb test smoke
pb task summarize
```

---

## 6. Adding MCP servers and Ollama

### 6.1 Why add MCP/Ollama

MCP servers and a small local LLM can make Promptbranch more Claude-Code-like by giving it local machine awareness.

They add:

- repo inspection
- git status/diff
- log analysis
- test execution
- artifact packaging
- local diagnostics
- structured command planning
- preflight checks before ChatGPT/project mutations

### 6.2 High-level architecture

```text
User
  ↓
pb CLI
  ↓
Local Orchestrator
  ├─ Ollama small LLM
  │   ├─ classify intent
  │   ├─ extract arguments
  │   ├─ summarize logs
  │   └─ propose safe plans
  ├─ MCP servers
  │   ├─ filesystem reader
  │   ├─ git reader
  │   ├─ test runner
  │   ├─ artifact/version scanner
  │   └─ Promptbranch state reader
  └─ Promptbranch service
      └─ ChatGPT.com execution surface
```

### 6.3 Role split

#### Ollama/local LLM may do

- classify user intent
- extract structured command arguments
- summarize logs before sending to ChatGPT
- choose diagnostic read-only commands
- generate JSON plans
- detect likely command namespace

#### Ollama/local LLM must not do directly

- delete sources
- overwrite artifacts
- choose release baselines alone
- approve destructive retries
- silently update `.pb_profile`
- run arbitrary shell commands
- mutate ChatGPT project state without deterministic prechecks

The local LLM proposes. A deterministic executor decides.

### 6.4 Recommended MCP servers

Start with read-only or constrained tools.

| MCP server | Purpose | Initial permission |
|---|---|---|
| Filesystem MCP | list/read repo files and logs | read-only |
| Git MCP | status, diff, branch, tags | read-only |
| Promptbranch state MCP | read current ws/task/artifact state | read-only |
| Test MCP | run bounded smoke/unit tests | controlled process |
| Artifact MCP | scan versions, package ZIPs, verify layout | gated source/artifact write |
| Promptbranch MCP | expose ws/task/src/artifact commands | gated writes |

Avoid starting with a broad unrestricted shell MCP.

### 6.5 Policy-gated executor

The local agent should emit structured intent:

```json
{
  "intent": "src_add",
  "args": {
    "file": "artifacts/example.zip"
  },
  "risk": "write",
  "requires_confirmation": false,
  "prechecks": [
    "workspace_selected",
    "file_exists",
    "basename_normalized",
    "duplicate_checked"
  ]
}
```

The deterministic executor validates:

- current workspace exists
- current task exists if required
- target file exists
- basename is normalized
- duplicate source state is known
- requested tool is allowed
- mutation has transactional verification

Only then execute.

### 6.6 Safety policy

Default permissions:

- local LLM may run read-only tools automatically
- write tools require deterministic prechecks
- destructive tools require extra guardrails or explicit confirmation
- state updates happen only after verified outcomes

This avoids giving a small local model control over destructive state.

---

## 7. Recommended implementation plan

### Phase 0 — model and safety boundary

Deliverables:

- formalize Workspace/Task/Artifact model
- formalize Message/Answer as task subresources
- define mutation result schema
- define allowed tool risk levels
- define `.pb_profile` state schema

Outcome:

- no ambiguity about state ownership or command semantics

### Phase 1 — canonical shell grammar

Deliverables:

```bash
pb ws list/use/current/leave
pb task list/use/current/leave/show
pb src list/add/rm
pb ask
```

Keep old commands as aliases temporarily, but document canonical grammar only.

Outcome:

- user workflow becomes coherent and scriptable

### Phase 2 — task messages and answers

Deliverables:

```bash
pb task messages list
pb task message show <id-or-index>
pb task message answer <id-or-index>
```

Internal model:

```text
Task
  Turn[]
    user_message
    assistant_answers[]
```

Outcome:

- a chat becomes inspectable as a structured task transcript

### Phase 3 — source/artifact lifecycle

Deliverables:

```bash
pb src sync <path>
pb artifact current
pb artifact list
pb artifact release
pb artifact verify
```

Rules:

- source sync packages repo snapshot
- duplicate source add is idempotent
- source replace/remove is transactional
- artifact release respects version and baseline continuity
- ZIP opens directly to repo contents, no wrapper folder

Outcome:

- Promptbranch compensates for ChatGPT's lack of native filesystem access

### Phase 4 — reliability layer

Deliverables:

```bash
pb doctor
pb test smoke
pb debug project-list
pb debug chats
pb debug sources
pb debug save-flow
```

Outcome:

- failures become diagnosable workflow regressions instead of random browser incidents

### Phase 5 — local MCP/Ollama orchestrator, read-only first

Deliverables:

```bash
pb agent plan "..."
pb agent doctor
pb agent inspect
```

Capabilities:

- Ollama intent classifier
- read-only filesystem MCP
- read-only git MCP
- Promptbranch state reader
- log summarizer

Outcome:

- local agent can understand repo/project context without mutating anything

### Phase 6 — controlled MCP writes

Deliverables:

- test runner MCP
- artifact packager MCP
- gated Promptbranch MCP tools

Rules:

- write tools require deterministic prechecks
- destructive tools require collateral-change detection
- state updates only after verification

Outcome:

- local control plane can safely execute Claude-Code-like workflow steps

### Phase 7 — full workflow loop

Target workflow:

```bash
pb ws use "Claude Code workflow in ChatGPT"
pb task new "Fix duplicate source add"
pb agent inspect
pb src sync .
pb ask "Analyze current bug with repo context"
pb artifact release
pb test smoke
pb task summarize
```

Outcome:

- Promptbranch functions as a practical Claude-Code-like shell around ChatGPT Projects.

---

## 8. Key risks

### 8.1 UI fragility

ChatGPT UI changes can break DOM automation.

Mitigation:

- backend-first reads
- DOM only as fallback
- debug artifacts for every brittle flow

### 8.2 Destructive retry loops

Source remove/add flows can cause collateral changes if retries are not guarded.

Mitigation:

- snapshot before mutation
- compare after failed attempts
- abort on collateral change
- never retry blindly

### 8.3 Premature refresh after save

Refreshing before a source save fully commits can abort persistence.

Mitigation:

- wait for dialog closed
- wait for surface idle
- wait for Add button visible
- dwell briefly
- only then verify persistence

### 8.4 Local LLM overreach

A small local model may misclassify or make weak decisions.

Mitigation:

- local LLM proposes JSON intent only
- deterministic executor validates
- no direct destructive tool access

### 8.5 State corruption

Bad local state can cause commands to operate on the wrong project/task.

Mitigation:

- `.pb_profile` inherited state
- explicit `pb ws current` and `pb task current`
- update state only after verification
- include project URL and conversation URL in every mutation result

---

## 9. Current priority recommendation

Do not start by adding many aliases or many MCP write tools.

Priority order:

1. formalize the model and schema
2. canonicalize `pb ws`, `pb task`, `pb src`, `pb artifact`
3. add task message/answer subresource commands
4. add `pb doctor` and `pb test smoke`
5. add read-only MCP/Ollama local agent
6. add controlled source/artifact write tools only after the above is stable

---

## 10. Verdict

### Strengths

- The Workspace/Task/Artifact model maps cleanly to ChatGPT Projects.
- Message/Answer as task subresources gives clear user semantics.
- MCP/Ollama can add the local repo awareness that ChatGPT Projects lack.
- Transactional writes directly address known failure modes.

### Weaknesses

- Promptbranch still cannot equal Claude Code's native local filesystem/edit loop.
- Browser/UI automation remains a reliability risk.
- A small local LLM is not trustworthy as an autonomous executor.

### Unknowns

- How much reliable message-level transcript data can be extracted backend-first.
- Whether all needed source metadata is available outside the DOM.
- Which local Ollama model is good enough for structured JSON intent extraction on the target machine.

### Next step

Implement Phase 1 and Phase 2 before adding write-capable MCP tools:

```bash
pb ws ...
pb task ...
pb src ...
pb ask
pb task messages list
pb task message show <id>
pb task message answer <id>
```

Then add `pb doctor`, `pb test smoke`, and read-only MCP/Ollama orchestration.

