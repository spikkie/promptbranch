# Promptbranch Claude-Code Shell — Previous Chat Summary

## Purpose

This note summarizes the previous implementation chat so it can be added as a ChatGPT Project source.

The project goal is to make **Promptbranch** behave like a constrained Claude-Code-like workflow shell around ChatGPT Projects:

- **Promptbranch CLI** = local control plane
- **ChatGPT Project** = workspace
- **ChatGPT chat/conversation** = task/session
- **Project sources** = repo snapshots, specs, logs, and release ZIPs
- **Generated ZIP artifacts** = release outputs
- **Test suite / doctor / debug artifacts** = regression and diagnosis layer

The target is not literal Claude Code parity. ChatGPT Projects do not provide a native filesystem/edit/test loop. The realistic target is the same workflow shape: select workspace, select task, sync context, ask, inspect results, package release, and validate.

---

## Core architecture decisions

### 1. Use three independent active scopes

Promptbranch should track exactly three active scopes:

```text
workspace = current ChatGPT Project
task      = current chat/conversation inside the project
artifact  = current repo/source/release ZIP reference
```

The state model must avoid conflating project selection, task selection, and release/source version selection.

### 2. Prefer `task` as the public term

The public shell grammar should use **task**.

Backend/internal code may still use **chat** or **conversation**, because that matches ChatGPT terminology and existing implementation names.

Clean naming rule:

```text
CLI/user-facing: task
Backend/internal: chat/conversation
Legacy aliases: chat-list, chats, chat-use, use-chat, chat-leave, chat-show
```

Do not add a new `pb chat` namespace. That would create two competing public grammars. Keep the old `chat-*` commands as legacy aliases and document `pb task ...` as canonical.

### 3. Backend-first reads, transactional writes

Reads should prefer:

1. backend JSON / network payload
2. saved Promptbranch state
3. DOM scraping
4. OCR/image fallback only as a last resort

Writes should follow a transaction pattern:

1. trigger action
2. wait for settled/backend-confirmed state
3. re-read and verify persistence
4. update Promptbranch state only after verification

Never assume success immediately after a click, and never refresh before commit/save is stable.

### 4. Known reliability lesson: early refresh aborting save

The earlier source-add failure was diagnosed as a timing/commit race, not a matching bug.

Failure pattern:

- source add appeared to start correctly
- the dialog/text area/save button were present
- persistence verification refreshed too soon
- a backend upload/commit request was aborted
- the Sources tab returned to an empty state

Correct rule:

```text
After Save, wait for:
- dialog closed
- Sources surface idle
- Add button visible again
- short stability dwell
Only then perform explicit persistence verification.
```

This lesson generalizes: UI transitions are not proof of persistence.

---

## Release timeline and accepted baselines

### v0.0.105 — pinned starting baseline

The work started from `chatgpt_claudecode_workflow_v0.0.105.zip`.

A baseline-resolution issue occurred first: the requested ZIP was not visible in `/mnt/data` during one attempt, and older ZIPs were rejected because using them would violate baseline continuity. Once `v0.0.105` was available as the project source, implementation continued from that baseline.

### v0.0.106 — Phase 0: model and safety boundary

Implemented Phase 0 plumbing only; no user-facing canonical shell grammar yet.

Added:

- `promptbranch_shell_model.py`
- `promptbranch/shell_model.py` re-export
- Workspace / Task / Artifact references
- UserMessage / AssistantAnswer / Turn model
- mutation result schema
- tool risk levels and precheck mapping
- normalized `.pb_profile` state snapshot sections:
  - `workspace`
  - `task`
  - `artifact`
- `remember_artifact()` and `forget_artifact()` state helpers
- focused tests in `tests/test_promptbranch_shell_model.py`

Validation used compile checks and direct assertion checks because pytest hung in the container. The user later tested locally.

### v0.0.107 — test hermeticity fix

The user hit failing CLI tests after `v0.0.106`.

Root cause:

- tests expected default service timeout `900.0`
- local config/environment caused `300.0`
- this was local config leaking into tests, not a Phase 0 model bug

Fix:

- made CLI tests hermetic
- forced test config to a missing temporary config path
- cleared `CHATGPT_SERVICE_TIMEOUT_SECONDS`

User confirmed `v0.0.107` solved the test issue. `v0.0.107` became the accepted baseline.

### v0.0.108 — Phase 1: canonical shell grammar

Implemented canonical wrappers around existing stable flows.

Added public grammar:

```bash
pb ws list/use/current/leave
pb task list/use/current/leave/show
pb src list/add/rm
pb test smoke
pb doctor
pb ask
```

Important design choice:

- wrappers reuse existing implementation paths
- browser/service behavior was not rewritten
- old command names remained available as aliases

User validation:

```text
67 passed in 0.76s
```

Test set:

```bash
python3 -m pytest \
  tests/test_cli_state.py \
  tests/test_promptbranch_cli.py \
  tests/test_cli_parser.py \
  -q
```

`v0.0.108` became the accepted baseline.

### v0.0.109 — Phase 2: task message/answer inspection

Implemented task subresource inspection:

```bash
pb task messages list
pb task message show <id-or-index>
pb task message answer <id-or-index>
```

Also supported optional task targeting:

```bash
pb task messages list <task>
pb task message show <id-or-index> --task <task>
pb task message answer <id-or-index> --task <task>
```

Implementation detail:

The existing chat payload is flat:

```text
user -> assistant -> user -> assistant
```

Phase 2 groups that into:

```text
message -> answers[]
```

This supports:

- user message with no answer after timeout
- user message with one answer
- user message with multiple/regenerated assistant answers

User validation:

```text
75 passed in 0.85s
```

Test set:

```bash
python3 -m pytest \
  tests/test_cli_state.py \
  tests/test_promptbranch_cli.py \
  tests/test_cli_parser.py \
  tests/test_promptbranch_shell_model.py \
  -q
```

`v0.0.109` became the accepted baseline.

### v0.0.110 — live selected-task hardening

The user live-tested Phase 2 and discovered that the workspace was selected but no current task was selected.

Observed state:

```text
project=claude-code-workflow-in-chatgpt
conversation_url=none
conversation_id=none
```

Therefore these commands failed correctly:

```bash
pb task messages list --json
pb task message show latest --json
```

Reason: message/answer commands inspect messages inside the current task/chat. They are task subresources, not workspace-level commands.

Correct live test sequence:

```bash
pb task list
pb task use <index-or-id-or-url>
pb task current
pb task messages list --json
pb task message show latest --json
pb task message answer latest --json
```

Alternative fresh-task sequence:

```bash
pb ask "live smoke test for task message extraction"
pb task current
pb task messages list --json
pb task message show latest --json
pb task message answer latest --json
```

The live test exposed a UX gap, not a transcript parsing failure: the command should provide better recovery hints when no current task is selected.

`v0.0.110` passed local regression and existing live suite, but the live suite did not yet cover Phase 2 message/answer commands.

### v0.0.111 — add `task_message_flow` to live test suite

Implemented a new live test-suite step:

```text
task_message_flow
```

It validates:

```text
ask creates/uses a task
task list can see the created task
task get/read returns transcript data
latest user message contains the smoke prompt
latest assistant answer contains TASK_MESSAGE_OK
```

Added selectors:

```bash
pb test-suite --only task_message_flow --json
pb test-suite --only task_messages --json
pb test-suite --only task --json
```

Naming cleanup:

- canonical public term is **task**
- legacy chat commands remain available but should be marked as aliases:

```text
chat-list  -> pb task list
chats      -> pb task list
chat-use   -> pb task use
use-chat   -> pb task use
chat-leave -> pb task leave
chat-show  -> pb task show
```

Also improved no-current-task recovery hints.

Validation in build environment:

```text
93 passed
```

User later reported:

```text
93 passed in 0.93s
```

### v0.0.112 / v0.0.113 — rate limiting and task visibility hardening

The live `task_message_flow` exposed timing/rate-pressure issues. The main concern was not making too many ChatGPT requests too quickly.

The implementation direction was to maximize reliability by:

- slowing post-ask visibility checks
- adding bounded low-rate polling after `ask`
- avoiding expensive conversation-history fallback until final visibility attempt
- adding knobs for safe timing:

```bash
--task-list-visible-timeout-seconds
--task-list-visible-poll-min-seconds
--task-list-visible-poll-max-seconds
--task-list-visible-max-attempts
```

`GET /v1/chats` was extended to support:

```text
include_history_fallback
```

`v0.0.113` was later verified to contain real changes compared with `v0.0.112`, including the new task-list visibility options and `include_history_fallback` behavior.

### v0.0.116 — cleanup of Python warning noise

By `v0.0.116`, escape warnings in browser-client JS snippets were fixed.

Changes included:

- fixed invalid `\s` / `\b` escape warnings in `promptbranch_browser_auth/client.py`
- converted affected `page.evaluate(...)` snippets to raw triple-quoted strings
- updated version references, README, Docker tag refs, tests, and `UPGRADING.md`

User validation:

```text
promptbranch 0.0.116
113 passed in 1.02s
```

However, the live suite still failed at:

```text
task_message_flow.task_list_visible
```

Conclusion: warning cleanup was useful hygiene, but probably not the root cause of the live task-list visibility issue.

### v0.0.117 — task-list visibility investigation started

The next planned release after `v0.0.116` was `v0.0.117`, focused narrowly on the live `task_message_flow.task_list_visible` bug.

Known state at that point:

- unit/static regression tests were passing
- the live suite still exposed task-list visibility inconsistency
- root cause likely lived in project-scoped chat/task listing or backend/history fallback behavior

---

## Current accepted/known state from the previous chat

Strongly supported:

- Phase 0 model/schema work is implemented.
- Phase 1 canonical grammar is implemented.
- Phase 2 message/answer inspection is implemented.
- Canonical public term should be `task`, not `chat`.
- Old `chat-*` commands should remain legacy aliases.
- Local pytest suites passed up to at least `v0.0.116`.

Not fully resolved:

- Live `task_message_flow` can still fail because the newly created/used task is not always visible in task listing quickly enough.
- The exact backend consistency delay after `ask` is still uncertain.
- The test suite should avoid aggressive polling or repeated expensive history lookups.

Most recent clear live failure target:

```text
task_message_flow.task_list_visible
```

---

## Practical testing commands

Regression tests used repeatedly:

```bash
python3 -m pytest \
  tests/test_cli_state.py \
  tests/test_promptbranch_cli.py \
  tests/test_cli_parser.py \
  tests/test_promptbranch_shell_model.py \
  tests/test_full_integration_harness.py \
  tests/test_project_list_browser_client.py \
  -q
```

Live test suite:

```bash
pb test-suite --json 2>&1 | tee pb_test-suite.<version>.full.log
```

Focused task-message flow:

```bash
pb test-suite --only task_message_flow --json \
  2>&1 | tee pb_test-suite.<version>.task_message_flow.log
```

Safer rate-limited live suite shape:

```bash
pb test-suite --json \
  --post-ask-delay-seconds 45 \
  --task-list-visible-max-attempts 3 \
  --task-list-visible-poll-min-seconds 30 \
  --task-list-visible-poll-max-seconds 60 \
  2>&1 | tee pb_test-suite.<version>.safe.log
```

---

## Critical assessment

### Strengths

- The project now has a coherent shell model: workspace/task/artifact.
- Canonical `pb ws`, `pb task`, `pb src`, `pb test`, `pb doctor`, and `pb ask` grammar exists.
- Message/answer inspection is modeled correctly as a task subresource.
- The test suite has been expanded from local parser/state checks toward live workflow validation.
- Baseline continuity discipline was maintained: every release builds from the latest accepted ZIP.
- ZIP packaging rules were preserved: repo contents at ZIP root, no wrapper folder.

### Weaknesses

- ChatGPT live consistency is still the main risk.
- `task_message_flow` depends on the backend exposing a newly used/created task soon after `ask`.
- Browser/UI automation remains brittle and must stay secondary to backend-first reads.
- Artifact/source lifecycle is still incomplete as a first-class Promptbranch feature.

### Unknowns

- How long after `ask` ChatGPT reliably exposes the conversation in project-scoped task listing.
- Whether project-scoped task listing and conversation-history fallback can be made reliable without causing rate pressure.
- Whether source metadata and artifact lifecycle can be implemented fully backend-first.

---

## Recommended next step

Continue from the latest accepted baseline in the previous chat.

If `v0.0.116` is the last confirmed local-pass baseline, then `v0.0.117` should remain narrowly scoped to:

1. diagnose/fix `task_message_flow.task_list_visible`
2. reduce rate pressure in live test-suite flow
3. prefer low-rate bounded polling over rapid retries
4. use expensive history fallback only as a final attempt
5. emit enough JSON diagnostics to distinguish:
   - task truly missing
   - task exists but not project-visible yet
   - backend fallback found it
   - transcript exists but task list did not expose it

Do not start Phase 3 source/artifact lifecycle until the Phase 2 live `task_message_flow` is stable.

## Verdict

✅ Strengths — the architecture is now coherent and testable, with model, grammar, and message inspection implemented.

⚠️ Weaknesses — live ChatGPT consistency and rate pressure remain the key blockers.

🔍 Unknowns — the exact consistency window for task visibility after `ask` is not yet known.

🧩 Next step — finish the `v0.0.117` task-list visibility fix before moving to Phase 3 (`pb src sync`, `pb artifact current/list/release/verify`).
