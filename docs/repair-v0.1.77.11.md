# Repair v0.1.77.11 — name-only non-anchor project cleanup fallback

## Base release

```text
base accepted/current: chatgpt_claudecode_workflow-2_v0.1.76.zip
failed intended repair: chatgpt_claudecode_workflow-2_v0.1.77.10.zip
repair version: v0.1.77.11
```

## Reason

`v0.1.77.10` release-control reached the live browser flow and failed at `project_remove_cleanup`.
The cleanup stack forwarded both `project_url` and `project_name`, but the browser removal code still searched mainly anchor-based sidebar project rows.
The exact project remained resolvable by name, while the remove operation could not find it in the sidebar.

## Scope

This is a repair-only change.

In scope:

```text
promptbranch_browser_auth/client.py
tests/test_project_resolve.py
version surfaces
docs/project/*
```

Out of scope:

```text
normal slice advancement
release-line advancement
repo-loop behavior
registry/adoption behavior
Project Source behavior
Docker service image behavior
```

## Change

Project cleanup now lets `_find_project_sidebar_container(...)` search non-anchor sidebar/menu candidates by exact project name, including:

```text
[data-sidebar-item="true"]
aside [role="button"]
aside button
nav [role="button"]
[role="menuitem"]
[role="option"]
[data-testid*="project"]
```

The existing project-id anchor path remains intact. The new fallback is used when ChatGPT renders the project row as a button/menu item rather than as a normal anchor.

## Validation performed

```text
focused project resolve/remove tests: run during packaging
project control-surface/version tests: run during packaging
compileall: run during packaging
bash syntax: run during packaging
ZIP hygiene: run during packaging
```

## No line advancement

```text
no normal release slice advanced
no release line advanced
no accepted/current baseline changed
```
