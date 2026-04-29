# How to use the stateful CLI

## Goal

Use `promptbranch` like a Git-style terminal tool that remembers the current project and chat.

## See the current state

```bash
promptbranch state
promptbranch state --json
```

## Show a compact prompt string

```bash
promptbranch prompt
```

Typical output looks like:

```text
promptbranch:My Project
promptbranch:My Project#69e512e8
```

## Clear remembered state

```bash
promptbranch state-clear
```

## Select a project or conversation

```bash
promptbranch use "My Project"
promptbranch use --pick
promptbranch use "https://chatgpt.com/g/.../project"
promptbranch use "https://chatgpt.com/g/.../c/..."
```

## Reuse remembered state

Once a project is remembered, project-scoped commands can omit `--project-url`.

```bash
promptbranch project-ensure "My Project"
promptbranch ask "hello"
```

## Canonical workspace/task commands

Prefer the canonical shell grammar for new scripts:

```bash
promptbranch ws current
promptbranch ws use "My Project"
promptbranch task list --json
promptbranch task use 1
promptbranch task current
```

Legacy `chat-*` commands still exist as aliases, but `task` is the public workflow term.

## Task-list visibility status

`promptbranch task list --json` includes `visibility_status`:

- `indexed`: task data came from indexed task sources such as snorlax/sidebar, DOM, history, or current page
- `recent_state_only`: task data came only from local recent-state recovery after `ask`
- `missing`: no task was visible

Treat `recent_state_only` as degraded. It keeps the workflow usable, but it is not proof that ChatGPT indexed the task.

`promptbranch task list` performs complete project-chat enumeration by combining indexed sources. It follows snorlax/sidebar cursors when available, scrolls the project Chats surface, and supplements visible DOM/snorlax results with conversation-history enumeration so tasks below the initially visible list are not silently omitted. If ChatGPT omits project ids from the conversation-history list payload, Promptbranch probes conversation detail payloads and reports recovered rows under `source_counts.history_detail`.

Plain `promptbranch task list` also prints a compact footer with `count`, `visibility`, and `sources`. Use `--json` when scripts need the full payload or need to distinguish `history` from `history_detail`.

## Debug task-list undercounts

When `promptbranch task list` stops at the first visible project-chat batch, collect diagnostics before changing enumeration logic again:

```bash
promptbranch debug chats --json \
  2>&1 | tee pb_debug_chats.json.log

promptbranch debug chats --json --scroll-rounds 30 --wait-ms 800 \
  2>&1 | tee pb_debug_chats_deep.json.log
```

The command writes an artifact directory containing:

- `summary.json`
- DOM snapshots before/after Chats tab activation
- per-round scroll diagnostics
- final screenshot and HTML
- snorlax/sidebar and conversation-history/detail observations

Use `--no-history` to focus on the visible Chats tab and scroll containers without exercising backend history/detail probes.

