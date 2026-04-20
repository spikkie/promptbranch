# How to set up shell completion and menu bar state

## Goal

Make the CLI easier to use interactively and expose the current project/chat in shell or menu-bar UI.

## Bash completion

```bash
eval "$(promptbranch completion bash)"
```

Persist it through your shell startup file if you want it every session.

## Zsh completion

```bash
mkdir -p ~/.zsh/completions
promptbranch completion zsh > ~/.zsh/completions/_promptbranch
```

## Fish completion

```bash
mkdir -p ~/.config/fish/completions
promptbranch completion fish > ~/.config/fish/completions/promptbranch.fish
```

## Menu-bar or shell prompt state

Use:

```bash
promptbranch prompt
```

or machine-readable output:

```bash
promptbranch state --json
```

A small status widget can poll one of these commands to show the current project and chat.
