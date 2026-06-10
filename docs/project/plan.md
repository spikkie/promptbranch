# Project Plan

## Current baseline

```text
accepted/current baseline with adoption evidence: chatgpt_claudecode_workflow-2_v0.1.70.1.zip
accepted checksum: 24be7e1c993d69ffb3ae50fbd50a45edf8a1af07ed616b107ef895698fc1ed33
next normal target: chatgpt_claudecode_workflow-2_v0.1.71.zip
release line: v0.1.x JSON orchestration / Promptbranch workflow control-plane hardening
```

## Plan summary

```text
Keep release slices narrow. v0.1.70.1 repaired explicit missing-repo lookup and is accepted/current by operator evidence. v0.1.71 introduces project-scoped multi-repo registry resolution so any joined repo can resolve the same project artifact registry without remembering a coordinator/main repo or manual --profile-dir.
```

## Release / slice plan

| Version | Slice | Goal | Scope | Out of scope | Expected validation | Status |
|---|---|---|---|---|---|---|
| v0.1.66 | Release doctor config-aware candidate ZIP precheck | Make release doctor consume `.promptbranch-release.yml` for read-only candidate ZIP inspection | release doctor/config docs and tests | install, upload Project Sources, adoption, state update, commit, push | focused release config/doctor/docs-status tests | accepted_current |
| v0.1.67 | Project MVP / DoD / Plan control surface migration | Create `docs/project/` and focused validator while preserving old docs | `docs/project/*`, `tests/test_project_control_surface.py`, release metadata | runtime behavior, deployment behavior, source mutation, artifact adoption, old-doc deletion | focused control-surface validator | superseded by later accepted baseline |
| v0.1.68 | Project Sources add performance and transactional diagnostics | Reduce new-source add latency and return safer diagnostics after overwrite/persistence failures | source-add preflight/verification path, focused source-add tests, project status docs | broad lifecycle rewrite, deployment behavior | full v0.1.68 test report supplied by operator | accepted_current |
| v0.1.69 | Browser-profile busy retry and source-add idle barrier | Prevent lifecycle adoption/source-list verification from racing a just-finished Project Source browser mutation | `pb browser wait-idle`, post-source-add idle barrier, structured busy payloads for `src list`/artifact adoption verification, focused tests, status docs | runtime ask behavior, deployment behavior, autonomous execution, broad release lifecycle migration | focused browser/source/adoption parser tests, project control-surface test, compileall, ZIP hygiene; adopted by operator evidence | accepted_current |
| v0.1.70 | Multi-repo artifact registry state | Make artifact current-state repo-scoped so one repo adoption cannot overwrite another repo baseline | `ArtifactRecord.repo_id`, repo-aware registry current/current_all, repo-scoped state, `pb artifact current --repo/--all`, adopt repo-prefix validation, focused tests, status docs | release-set orchestration, dependency solving, multi-repo lifecycle execution, Project Source upload changes, ZIP packaging changes | focused artifact/state/CLI tests, project control-surface test, compileall, ZIP hygiene, operator adoption evidence | accepted_current |
| v0.1.70.1 | Repair missing repo artifact-current fallback | Explicit `pb artifact current --repo <missing>` must fail closed without returning another repo artifact as state | `promptbranch_state.py`, `promptbranch_cli.py`, focused tests, repair note, status docs, version metadata | line advancement, release-set orchestration, project declaration, dependency solving, lifecycle behavior changes | missing-repo focused tests, existing artifact-current focused tests, project control-surface test, compileall, ZIP hygiene, operator adoption evidence | accepted_current |
| v0.1.71 | Project-scoped multi-repo registry resolution | Make any joined repo resolve the same project artifact registry without remembering a coordinator/main repo | `.promptbranch-repo.json` support, user-local project registry path, `pb project join/status`, `pb repo list/doctor`, artifact current --all project diagnostics, focused tests, docs | release-set orchestration, dependency solving, automatic Project Source upload, automatic adoption, Git/deployment operations across repos | project/repo focused tests, artifact-current regression tests, project control-surface test, compileall, ZIP hygiene | candidate |

## Slice definition — v0.1.71 normal release

```text
Release: v0.1.71
Baseline: chatgpt_claudecode_workflow-2_v0.1.70.1.zip accepted/current with operator adoption evidence.
Type: normal candidate
Slice: Project-scoped multi-repo registry resolution
Goal: allow any repo joined to a Promptbranch project to resolve the same project-level artifact registry automatically, without requiring operators or other developers to remember a coordinator repo or manual --profile-dir.
In scope: `.promptbranch-repo.json`, `pb project join --json`, `pb project status --json`, `pb repo list --json`, `pb repo doctor --json`, project-derived registry path under user-local state, artifact current --all project diagnostics, focused tests, release/status docs, version metadata.
Out of scope: release-set orchestration, cross-repo dependency solving, automatic Project Source upload, automatic artifact adoption, Git operations across repos, deployment orchestration, making one repo the main repo.
Expected files: `promptbranch_project.py`, `promptbranch_repos.py`, `promptbranch_artifacts.py`, `promptbranch_state.py`, `promptbranch_cli.py`, `tests/test_promptbranch_project.py`, `tests/test_promptbranch_repos.py`, existing artifact/current focused tests, `docs/project/*`, `docs/release-v0.1.71.md`, `.promptbranch-repo.example.json`, `docs/promptbranch-multi-repo-projects.md`, version files.
Expected validation: project/repo focused pytest, artifact-current regression tests, project control-surface pytest, Python compileall, ZIP hygiene, clean extraction focused validation.
DoD movement: add DOD-016 for project-scoped multi-repo registry resolution; mark done after focused validation passes.
Risk: project registry storage changes where artifact current-state is read/written for joined repos; explicit --profile-dir remains the debug/override escape hatch.
Next step: package candidate ZIP and require operator install/test/adoption evidence before treating it as accepted/current.
```
