# How to manage projects and sources

## Goal

Create a project, add sources, and remove them cleanly.

## Create a project

```bash
promptbranch project-create "Demo Project" --icon folder --color blue
```

## Resolve or ensure a project

```bash
promptbranch project-resolve "Demo Project"
promptbranch project-ensure "Demo Project"
```

## Add a text source

```bash
promptbranch --project-url https://chatgpt.com/g/.../project   project-source-add --type text --value "Reference notes" --name Notes
```

## Add a file source

```bash
promptbranch --project-url https://chatgpt.com/g/.../project   project-source-add --type file --file ./docs/spec.pdf --name Spec
```

## Remove a source

```bash
promptbranch --project-url https://chatgpt.com/g/.../project   project-source-remove "Spec" --exact
```

## Remove the project

```bash
promptbranch --project-url https://chatgpt.com/g/.../project project-remove
```

## Sync the current repo as a source snapshot

Create a local snapshot only:

```bash
promptbranch src sync . --no-upload --json
```

Create a snapshot and upload it to the current workspace as a project source:

```bash
promptbranch ws use "Demo Project"
promptbranch src sync . --json
```

Use `promptbranch artifact current`, `promptbranch artifact list`, and `promptbranch artifact verify` to inspect generated ZIPs.
