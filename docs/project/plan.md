# Project Plan

## Current baseline

```text
accepted/current baseline with adoption evidence: chatgpt_claudecode_workflow-2_v0.1.66.zip
accepted checksum: 2b05556677346aa2f9e1d7449bb1c70fc0c54b8d7cd130f22b6e7083960ec8a3
build input for this candidate: chatgpt_claudecode_workflow-2_v0.1.67.zip, per explicit operator v0.1.68 request
next normal target: chatgpt_claudecode_workflow-2_v0.1.68.zip
release line: v0.1.x JSON orchestration / Promptbranch workflow control-plane hardening
```

## Plan summary

```text
Keep release slices narrow. After the v0.1.67 project-control-surface migration, v0.1.68 narrows to Project Sources add performance and transactional diagnostics only. It does not widen lifecycle automation, adoption, deployment, or runtime behavior outside source-add handling.
```

## Release / slice plan

| Version | Slice | Goal | Scope | Out of scope | Expected validation | Status |
|---|---|---|---|---|---|---|
| v0.1.66 | Release doctor config-aware candidate ZIP precheck | Make release doctor consume `.promptbranch-release.yml` for read-only candidate ZIP inspection | release doctor/config docs and tests | install, upload Project Sources, adoption, state update, commit, push | focused release config/doctor/docs-status tests | accepted_current |
| v0.1.67 | Project MVP / DoD / Plan control surface migration | Create `docs/project/` and focused validator while preserving old docs | `docs/project/*`, `tests/test_project_control_surface.py`, release metadata | runtime behavior, deployment behavior, source mutation, artifact adoption, old-doc deletion | focused control-surface validator | candidate / build input for v0.1.68 |
| v0.1.68 | Project Sources add performance and transactional diagnostics | Reduce new-source add latency and return safer diagnostics after overwrite/persistence failures | `promptbranch_browser_auth/client.py`, compatibility mirror `chatgpt_browser_auth/client.py`, focused source-add tests, project status docs | source lifecycle adoption, broad UI rewrite, backend-only source API, deployment behavior, full native release lifecycle | targeted source-add tests, control-surface test, compile, ZIP hygiene | candidate |

## Slice definition — v0.1.68

```text
Release: v0.1.68
Baseline: chatgpt_claudecode_workflow-2_v0.1.67.zip as explicit build input; last adoption-evidenced baseline remains v0.1.66.
Type: normal candidate
Slice: Project Sources add performance and transactional diagnostics
Goal: make add-new-source faster when the initial Sources snapshot is empty, reduce absence preflight for non-empty misses, and return structured recovery guidance when overwrite/persistence verification fails.
In scope: source-add preflight path, overwrite failure result shape, persistence false-negative diagnostics, focused tests, version metadata, docs/project status updates.
Out of scope: source adoption state changes, Project Source API replacement, source sync rewrite, release lifecycle automation, deployment changes, old-doc deletion.
Expected files: `promptbranch_browser_auth/client.py`, `chatgpt_browser_auth/client.py`, `tests/test_project_source_capabilities.py`, version files, `docs/project/*`, `docs/release-v0.1.68.md`.
Expected validation: targeted source-add pytest selection, project control-surface pytest, Python compileall, ZIP hygiene.
DoD movement: DOD-012 is introduced and moved to done when focused source-add tests pass; DOD-009 moves to done after ZIP hygiene.
Risk: empty initial source snapshots can be stale; recovery guidance must prevent blind repeated overwrites after verification ambiguity.
Next step: install/test v0.1.68 candidate and provide `pb artifact current --json` only after adoption.
```
