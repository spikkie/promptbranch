# Project Plan

## Current baseline

```text
accepted/current baseline: chatgpt_claudecode_workflow-2_v0.1.66.zip
accepted checksum: 2b05556677346aa2f9e1d7449bb1c70fc0c54b8d7cd130f22b6e7083960ec8a3
next normal target: chatgpt_claudecode_workflow-2_v0.1.67.zip
release line: v0.1.x JSON orchestration / Promptbranch workflow control-plane hardening
```

## Plan summary

```text
Create a canonical docs/project/ control surface first, then continue narrow read-only or guarded lifecycle slices from the accepted baseline. Do not widen runtime behavior as part of the documentation migration.
```

## Release / slice plan

| Version | Slice | Goal | Scope | Out of scope | Expected validation | Status |
|---|---|---|---|---|---|---|
| v0.1.66 | Release doctor config-aware candidate ZIP precheck | Make release doctor consume `.promptbranch-release.yml` for read-only candidate ZIP inspection | release doctor/config docs and tests | install, upload Project Sources, adoption, state update, commit, push | focused release config/doctor/docs-status tests | accepted_current |
| v0.1.67 | Project MVP / DoD / Plan control surface migration | Create `docs/project/` and focused validator while preserving old docs | `docs/project/*`, `tests/test_project_control_surface.py`, release metadata | runtime behavior, deployment behavior, source mutation, artifact adoption, old-doc deletion | focused control-surface validator | candidate |
| v0.1.68 | Next narrow controlled slice | Continue from accepted v0.1.67 after adoption evidence | TBD from `docs/project/status.md` after adoption | broad lifecycle automation unless explicitly scoped | targeted tests plus relevant guards | planned |

## Slice definition — v0.1.67

```text
Release: v0.1.67
Baseline: chatgpt_claudecode_workflow-2_v0.1.66.zip
Type: normal
Slice: Project MVP / DoD / Plan control surface migration
Goal: make docs/project/ the canonical continuation surface.
In scope: docs/project/README.md, mvp.md, definition-of-done.md, plan.md, status.md, release-status.md, decisions.md, migration.md, tests/test_project_control_surface.py, version metadata required for a canonical release artifact.
Out of scope: runtime behavior changes, deployment changes, source mutation changes, artifact adoption, old planning document deletion, unrelated MVP scope advancement.
Expected files: docs/project/* and tests/test_project_control_surface.py.
Expected validation: focused control-surface pytest plus package hygiene checks.
DoD movement: DOD-001 through DOD-007 move to done; adoption-related rows remain open until evidence.
Risk: stale existing docs may be over-trusted if not mapped explicitly.
Next step: install/test/adopt candidate and provide pb artifact current --json evidence.
```
