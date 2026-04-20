# How to install the promptbranch CLI

## Goal

Install the `promptbranch` command so it can be used like a normal terminal tool.

## Option 1: Install from a release zip with `pipx`

This is the best choice for command-line use because it keeps the tool isolated from your main Python environment.

```bash
pipx install ./chatgpt_claudecode_workflow_v0.0.73.zip
```

After install:

```bash
promptbranch --help
promptbranch state
promptbranch prompt
```

## Option 2: Install from an extracted checkout

Use this when developing locally.

```bash
python -m pip install .
```

## Verify the install

```bash
promptbranch --help
promptbranch completion bash | head
promptbranch state --json
```

## Upgrade to a new release

```bash
pipx upgrade promptbranch
```

If you install from a local zip instead of an index, reinstall from the new artifact.

## Remove the CLI

```bash
pipx uninstall promptbranch
```
