# Promptbranch canonical learning path

All audiences use the same concepts and authority model. Only the delivery adapter changes.

## Stage 0 — Orientation

Read `PROMPTBRANCH_OVERVIEW.md` and `GLOSSARY.md`. Goal: explain repository, Project/workspace, task/conversation, skill/tool, artifact and accepted/current in your own words.

## Stage 1 — Authority before commands

Read `AUTHORITY_MODEL.md`. Goal: distinguish read, plan, execute, mutate, publish, accept, adopt and deploy authority.

## Stage 2 — Read-only inspection

Read `QUICKSTART.md`. Use `pb skill list`, `pb skill validate`, `pb ws current --json`, `pb task current --json`, `pb artifact current --json`, and repository inspection as applicable. Goal: identify state without mutation.

## Stage 3 — Operator model

Read `OPERATOR_GUIDE.md` and the `promptbranch-operator` skill. Goal: classify an operation, list its preconditions and evidence, and state when to fail closed.

## Stage 4 — Developer model

Read `DEVELOPER_GUIDE.md` and the embedded `promptbranch-tool-authoring` skill. Goal: understand how PB extensions remain deterministic, schema-bound and proposal-only until separately authorized.

## Stage 5 — Exercises

Complete every exercise in `EXERCISES.md`. Goal: produce evidence/verdicts rather than narrative confidence.

## Audience adapters

### Human

Start at this file, use the Markdown materials directly, and perform exercises in a disposable/read-only context first.

### ChatGPT Project

Upload/import `PROJECT_SOURCE.md` as the primary Project Source. It contains the complete learning contract and reading order. Use the other files for focused reference.

### Claude or another coding agent

Read `AGENTS.md` first. It points to the same canonical curriculum and explicitly preserves PB's authority boundary. `CLAUDE.md` provides a concise Claude-oriented bootstrap without defining a separate PB behavior.

### PB-aware agent

Read `SKILL.md` and `manifest.json`; verify the bundle before trusting its contents. Follow the same learning stages and do not infer mutation authority from the bundle.
