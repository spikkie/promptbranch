# Project Plan

## Current baseline

```text
accepted/current baseline for repair: chatgpt_claudecode_workflow-2_v0.1.71.zip (operator stated fully tested/adopted; checksum evidence not recorded in this file); v0.1.71.1 was not installable due missing root `.gitignore`; v0.1.71.2 was rejected for protected `.pb_profile/` ZIP entries; v0.1.71.3 exposed a release-control service health version-format mismatch
accepted checksum: pending explicit v0.1.71 adoption evidence block
next normal target: chatgpt_claudecode_workflow-2_v0.1.72.zip
release line: v0.1.x JSON orchestration / Promptbranch workflow control-plane hardening
```

## Plan summary

```text
Keep release slices narrow. v0.1.70.1 repaired explicit missing-repo lookup and is accepted/current by operator evidence. v0.1.71 introduced project-scoped multi-repo registry resolution. v0.1.71.1 is a narrow repair that makes project join create/read the project registry and ensures `pb artifact current --all`, `pb repo list`, and `pb repo doctor` all use the same project-scoped registry from any joined repo. v0.1.71.2 is a packaging repair that restores the required root `.gitignore` omitted from the v0.1.71.1 ZIP. v0.1.71.3 removes protected `.pb_profile/` packaging. v0.1.71.4 normalizes service health version comparison between bare package versions and canonical `v` versions.
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
| v0.1.71 | Project-scoped multi-repo registry resolution | Make any joined repo resolve the same project artifact registry without remembering a coordinator/main repo | `.promptbranch-repo.json` support, user-local project registry path, `pb project join/status`, `pb repo list/doctor`, artifact current --all project diagnostics, focused tests, docs | release-set orchestration, dependency solving, automatic Project Source upload, automatic adoption, Git/deployment operations across repos | project/repo focused tests, artifact-current regression tests, project control-surface test, compileall, ZIP hygiene | accepted_current by operator statement; explicit adoption JSON not recorded here |
| v0.1.71.1 | Repair project registry command alignment | Ensure join creates project registry and artifact-current/repo diagnostics all use the project registry when no explicit `--profile-dir` is supplied | profile-dir explicitness tracking, project registry creation, artifact current --all configured-repo visibility, focused tests, repair note | normal v0.1.72 scope, import/migration command, release-set orchestration, adoption semantics | project/repo focused tests, artifact-current regression tests, project control-surface test, compileall, ZIP hygiene | rejected: missing required root `.gitignore` |
| v0.1.71.2 | Repair v0.1.71.1 ZIP root completeness | Restore required root `.gitignore` while preserving v0.1.71.1 behavior | `.gitignore`, version metadata, repair/status docs | normal v0.1.72 scope, behavior changes, release-set orchestration | required-root-file check, project/repo focused tests, project control-surface test, compileall, ZIP hygiene | rejected: protected `.pb_profile/` ZIP entry |
| v0.1.71.3 | Repair protected ZIP entry hygiene | Remove protected local Promptbranch state from repair ZIP while preserving v0.1.71.1/v0.1.71.2 behavior | ZIP payload hygiene, version metadata, repair/status docs | normal v0.1.72 scope, behavior changes, release-set orchestration | install ZIP guard, required-root and protected-entry checks, focused tests, compileall, ZIP hygiene | rejected: service health version-format mismatch |

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


## Repair definition — v0.1.71.1

```text
Release: v0.1.71.1
Base release: v0.1.71
Type: repair candidate
Slice advanced: no
Reason: v0.1.71 field testing showed `pb repo list` and `pb repo doctor` used the new project registry while `pb artifact current --all` could still use the resolved repo-local `.pb_profile`, because default profile resolution was mistaken for an explicit `--profile-dir`.
In scope: track whether `--profile-dir` was actually provided, create the project registry during `pb project join`, include locally configured repo IDs in project `current --all`, and ensure repo/list/doctor/artifact-current share the project registry by default from joined repos.
Out of scope: release-set orchestration, automatic Project Source upload, automatic artifact adoption, registry import/migration command, dependency solving, deployment behavior.
Expected validation: focused project/repo/artifact-current tests, project control-surface test, compileall, ZIP hygiene, clean extraction focused validation.
```


## Repair definition — v0.1.71.2

```text
Release: v0.1.71.2
Base release: v0.1.71.1 candidate
Type: repair candidate
Slice advanced: no
Reason: v0.1.71.1 failed install ZIP import guard because required root `.gitignore` was missing.
In scope: restore `.gitignore`, update version metadata, add repair note/status docs, preserve all v0.1.71.1 behavior.
Out of scope: normal v0.1.72 work, release-set orchestration, Project Source upload automation, artifact adoption semantics, deployment behavior.
Expected validation: required root-file check, focused project/repo/artifact-current tests, project control-surface test, compileall, ZIP hygiene, clean extraction focused validation.
```


## Repair definition — v0.1.71.3

```text
Release: v0.1.71.3
Base release: v0.1.71.2 candidate
Type: repair candidate
Slice advanced: no
Reason: v0.1.71.2 failed install ZIP import guard because protected `.pb_profile/` local state was packaged.
In scope: remove protected local Promptbranch state from ZIP payload, preserve required root files, update version metadata and repair docs.
Out of scope: normal v0.1.72 work, project registry changes, release-set orchestration, artifact adoption semantics, deployment behavior.
Expected validation: protected-entry check, required-root check, focused tests, project control-surface test, compileall, ZIP hygiene, clean extraction validation.
```


## Repair definition — v0.1.71.4

```text
Release: v0.1.71.4
Base release: v0.1.71.3 candidate
Type: repair candidate
Slice advanced: no
Reason: v0.1.71.3 reached a healthy service endpoint returning canonical `v0.1.71.3`, but the release-control service wait gate expected bare `0.1.71.3` and treated the leading `v` as a mismatch.
In scope: normalize one leading `v` in service health version comparison, prefer `package_version` when health JSON provides it, add focused shell-script regression tests, update repair/status docs and version metadata.
Out of scope: Docker build behavior beyond avoiding this false mismatch, project registry behavior, release-set orchestration, Project Source upload automation, artifact adoption semantics, deployment behavior.
Expected validation: focused shell-script health-probe tests, project control-surface test, compileall, ZIP hygiene, clean extraction focused validation.
```
