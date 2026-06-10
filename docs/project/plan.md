# Project Plan

## Current baseline

```text
accepted/current baseline with adoption evidence: chatgpt_claudecode_workflow-2_v0.1.69.zip
accepted checksum: 2132bec14263f3418cec5707211bd0931dd4d9928c7e8ae50bcb3e9fc3997b56
next normal target: chatgpt_claudecode_workflow-2_v0.1.70.zip
release line: v0.1.x JSON orchestration / Promptbranch workflow control-plane hardening
```

## Plan summary

```text
Keep release slices narrow. v0.1.70 fixes the multi-repo artifact baseline contamination risk by making artifact registry current-state and local project artifact/source state repo-scoped. It does not implement release-set orchestration or cross-repo lifecycle execution.
```

## Release / slice plan

| Version | Slice | Goal | Scope | Out of scope | Expected validation | Status |
|---|---|---|---|---|---|---|
| v0.1.66 | Release doctor config-aware candidate ZIP precheck | Make release doctor consume `.promptbranch-release.yml` for read-only candidate ZIP inspection | release doctor/config docs and tests | install, upload Project Sources, adoption, state update, commit, push | focused release config/doctor/docs-status tests | accepted_current |
| v0.1.67 | Project MVP / DoD / Plan control surface migration | Create `docs/project/` and focused validator while preserving old docs | `docs/project/*`, `tests/test_project_control_surface.py`, release metadata | runtime behavior, deployment behavior, source mutation, artifact adoption, old-doc deletion | focused control-surface validator | superseded by later accepted baseline |
| v0.1.68 | Project Sources add performance and transactional diagnostics | Reduce new-source add latency and return safer diagnostics after overwrite/persistence failures | source-add preflight/verification path, focused source-add tests, project status docs | broad lifecycle rewrite, deployment behavior | full v0.1.68 test report supplied by operator | accepted_current |
| v0.1.69 | Browser-profile busy retry and source-add idle barrier | Prevent lifecycle adoption/source-list verification from racing a just-finished Project Source browser mutation | `pb browser wait-idle`, post-source-add idle barrier, structured busy payloads for `src list`/artifact adoption verification, focused tests, status docs | runtime ask behavior, deployment behavior, autonomous execution, broad release lifecycle migration | focused browser/source/adoption parser tests, project control-surface test, compileall, ZIP hygiene; adopted by operator evidence | accepted_current |
| v0.1.70 | Multi-repo artifact registry state | Make artifact current-state repo-scoped so one repo adoption cannot overwrite another repo baseline | `ArtifactRecord.repo_id`, repo-aware `ArtifactRegistry.current/current_all`, repo-scoped `ConversationStateStore.artifacts_by_repo`, `pb artifact current --repo/--all`, adopt repo-prefix validation, focused tests, status docs | release-set orchestration, dependency solving, multi-repo lifecycle execution, Project Source upload changes, ZIP packaging changes | focused artifact/state/CLI tests, project control-surface test, compileall, ZIP hygiene | candidate |

## Slice definition — v0.1.70

```text
Release: v0.1.70
Baseline: chatgpt_claudecode_workflow-2_v0.1.69.zip accepted/current with operator adoption evidence.
Type: normal candidate
Slice: Multi-repo artifact registry state
Goal: make Promptbranch artifact current-state repo-scoped so adopting or registering one repo ZIP cannot overwrite or obscure another repo's accepted baseline in the same ChatGPT Project.
In scope: `ArtifactRecord.repo_id`, repo-aware registry current/current_all, repo-scoped state under `artifacts_by_repo`, `pb artifact current --repo`, `pb artifact current --all`, ambiguous unscoped current failure when multiple repo scopes exist, adopt repo-prefix validation, focused tests, version metadata, docs/project status updates.
Out of scope: release-set orchestration, cross-repo dependency solving, multi-repo lifecycle execution, Project Source upload behavior, ZIP packaging behavior, deployment behavior, broad release lifecycle ownership.
Expected files: `promptbranch_artifacts.py`, `promptbranch_state.py`, `promptbranch_cli.py`, `tests/test_promptbranch_artifacts.py`, `tests/test_cli_state.py`, `tests/test_promptbranch_cli.py`, version files, `docs/project/*`, `docs/release-v0.1.70.md`.
Expected validation: targeted artifact/state/CLI tests, project control-surface pytest, Python compileall, ZIP hygiene.
DoD movement: add DOD-014 for multi-repo artifact current-state isolation; move done after focused tests pass; DOD-009 moves to done after ZIP hygiene.
Risk: unscoped current must remain compatible for single-repo profiles but must fail closed for multi-repo profiles.
Next step: install/test v0.1.70 candidate; do not mark accepted/current until repo-scoped `pb artifact current` evidence confirms alignment.
```
