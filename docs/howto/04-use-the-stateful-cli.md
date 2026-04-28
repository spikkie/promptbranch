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

`promptbranch task list` performs complete project-chat enumeration by combining indexed sources. It follows snorlax/sidebar cursors when available, scrolls the project Chats surface, and supplements visible DOM/snorlax results with conversation-history enumeration so tasks below the initially visible list are not silently omitted.

Plain `promptbranch task list` also prints a compact footer with `count`, `visibility`, and `sources`. Use `--json` when scripts need the full payload.
