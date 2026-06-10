# Project Plan

## Current baseline

```text
accepted/current baseline with adoption evidence: chatgpt_claudecode_workflow-2_v0.1.70.zip
accepted checksum: 99836251f6b07798d2e4c1e8bf978f001dccb0cced6fb64446dd7f098fe620e9
next repair target: chatgpt_claudecode_workflow-2_v0.1.70.1.zip
next normal target after accepted repair: chatgpt_claudecode_workflow-2_v0.1.71.zip
release line: v0.1.x JSON orchestration / Promptbranch workflow control-plane hardening
```

## Plan summary

```text
Keep release slices narrow. v0.1.70 introduced repo-scoped artifact current-state and was adopted/current by operator evidence. v0.1.70.1 is a repair-only release that fixes the remaining explicit missing-repo lookup fallback defect without advancing the line or adding multi-repo project-declaration behavior.
```

## Release / slice plan

| Version | Slice | Goal | Scope | Out of scope | Expected validation | Status |
|---|---|---|---|---|---|---|
| v0.1.66 | Release doctor config-aware candidate ZIP precheck | Make release doctor consume `.promptbranch-release.yml` for read-only candidate ZIP inspection | release doctor/config docs and tests | install, upload Project Sources, adoption, state update, commit, push | focused release config/doctor/docs-status tests | accepted_current |
| v0.1.67 | Project MVP / DoD / Plan control surface migration | Create `docs/project/` and focused validator while preserving old docs | `docs/project/*`, `tests/test_project_control_surface.py`, release metadata | runtime behavior, deployment behavior, source mutation, artifact adoption, old-doc deletion | focused control-surface validator | superseded by later accepted baseline |
| v0.1.68 | Project Sources add performance and transactional diagnostics | Reduce new-source add latency and return safer diagnostics after overwrite/persistence failures | source-add preflight/verification path, focused source-add tests, project status docs | broad lifecycle rewrite, deployment behavior | full v0.1.68 test report supplied by operator | accepted_current |
| v0.1.69 | Browser-profile busy retry and source-add idle barrier | Prevent lifecycle adoption/source-list verification from racing a just-finished Project Source browser mutation | `pb browser wait-idle`, post-source-add idle barrier, structured busy payloads for `src list`/artifact adoption verification, focused tests, status docs | runtime ask behavior, deployment behavior, autonomous execution, broad release lifecycle migration | focused browser/source/adoption parser tests, project control-surface test, compileall, ZIP hygiene; adopted by operator evidence | accepted_current |
| v0.1.70 | Multi-repo artifact registry state | Make artifact current-state repo-scoped so one repo adoption cannot overwrite another repo baseline | `ArtifactRecord.repo_id`, repo-aware registry current/current_all, repo-scoped state, `pb artifact current --repo/--all`, adopt repo-prefix validation, focused tests, status docs | release-set orchestration, dependency solving, multi-repo lifecycle execution, Project Source upload changes, ZIP packaging changes | focused artifact/state/CLI tests, project control-surface test, compileall, ZIP hygiene, operator adoption evidence | accepted_current |
| v0.1.70.1 | Repair missing repo artifact-current fallback | Explicit `pb artifact current --repo <missing>` must fail closed without returning another repo artifact as state | `promptbranch_state.py`, `promptbranch_cli.py`, focused tests, repair note, status docs, version metadata | line advancement, release-set orchestration, project declaration, dependency solving, lifecycle behavior changes | missing-repo focused tests, existing artifact-current focused tests, project control-surface test, compileall, ZIP hygiene | candidate |

## Slice definition — v0.1.70.1 repair

```text
Release: v0.1.70.1
Baseline: chatgpt_claudecode_workflow-2_v0.1.70.zip accepted/current with operator adoption evidence.
Type: repair candidate
Slice: Missing repo artifact-current fallback repair
Goal: when an explicit repo_id is requested and no repo-scoped state or registry entry exists, return repo_current_not_found instead of falling back to legacy/global artifact state.
In scope: prevent explicit repo lookup fallback in `ConversationStateStore.snapshot`, return `repo_current_not_found` from `pb artifact current --repo <missing>`, keep non-JSON output safe, add focused regression tests, update repair/status docs and version metadata.
Out of scope: formal main/coordinator repo configuration, `.promptbranch-repos.json`, `pb repo list`, release-set orchestration, cross-repo dependency solving, multi-repo lifecycle execution, Project Source upload behavior, ZIP packaging behavior, deployment behavior.
Expected files: `promptbranch_state.py`, `promptbranch_cli.py`, `tests/test_cli_state.py`, `tests/test_promptbranch_cli.py`, version files, `docs/project/*`, `docs/repair-v0.1.70.1.md`.
Expected validation: targeted missing-repo tests, artifact-current focused tests, project control-surface pytest, Python compileall, ZIP hygiene.
DoD movement: add DOD-015 for explicit missing-repo lookup fail-closed behavior; mark done after focused tests pass.
Risk: behavior is intentionally stricter for typo/missing repo ids; valid repo and `--all` behavior must remain unchanged.
Next step: package candidate ZIP and require operator lifecycle/adoption evidence before treating it as accepted/current.
```
