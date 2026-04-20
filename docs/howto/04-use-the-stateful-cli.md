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
