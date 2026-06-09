# Release v0.1.58 — PB application design documentation and diagrams

## Base release

```text
chatgpt_claudecode_workflow-2_v0.1.57.zip
```

## Purpose

This documentation release records the application-level design of Promptbranch
(`pb`) and makes the role split between `pb` and ChatGPT explicit. It adds a
Markdown design document with activity, data-flow, and state-transition diagrams
and extends the existing editable draw.io sources rather than introducing a
parallel diagram format.

## Scope

Added:

```text
docs/design/promptbranch-application-design.md
tests/test_promptbranch_application_design_doc.py
```

Updated:

```text
VERSION
pyproject.toml
promptbranch_version.py
docs/design/promptbranch-class-diagram.drawio
docs/design/promptbranch-mvp-living-design.drawio
docs/diagrams/promptbranch-lifecycle/promptbranch_lifecycle_commands.drawio
docs/design/promptbranch-mvp-living-design.md
docs/design/promptbranch-mvp-gap-analysis.md
docs/design/orchestration/docs/current_status.md
```

## Diagram coverage

The release extends the current draw.io files with these pages:

```text
PB Application Role Components
PB Application Activity — pb and ChatGPT Roles
PB Application Data Flow
PB Application State Transitions
PB Release State Transitions
```

## Design boundary

This is a documentation/design source release only:

```text
runtime_state_mutation_allowed = false
source_mutation_allowed        = false
artifact_adoption_allowed      = false
deployment_allowed             = false
browser_automation_changed      = false
model_may_execute              = false
```

## Non-goals

This release does not add:

```text
- new CLI commands
- new backend API calls
- new browser automation behavior
- new source mutation behavior
- new artifact adoption behavior
- runtime orchestration engine
- Kubernetes game implementation
- Ollama/local LLM execution authority
```

## Validation performed

```text
python3 -m pytest -q tests/test_promptbranch_application_design_doc.py
python3 promptbranch_cli.py release docs-status --version v0.1.58 --json
python3 -m compileall -q .
```
