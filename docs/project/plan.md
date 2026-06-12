# Project Plan

## Current baseline

```text
accepted/current baseline: chatgpt_claudecode_workflow-2_v0.1.73.4.zip
accepted checksum: a76aa4292bb8aba31c8223ae5342b6e9a731b4aef3a5505581d719d263fa1858
next normal target: chatgpt_claudecode_workflow-2_v0.1.74.zip
release line: v0.1.x JSON orchestration / Promptbranch workflow control-plane hardening
```

## Plan summary

```text
Keep release slices narrow. v0.1.73.4 is accepted/current. v0.1.74 is a normal release-validation coverage slice that turns the focused regression suites from the v0.1.73.x repair line into explicit release-validation groups inside `pb test full` and release-control reporting.
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
| v0.1.71.4 | Repair service health version normalization | Normalize release-control service health comparison between bare and canonical `v` versions | release-control health wait gate, focused shell-script tests, version metadata, repair/status docs | project-registry behavior, Docker build behavior beyond avoiding false mismatch, adoption semantics | focused shell-script health-probe tests, control-surface test, compileall, ZIP hygiene | rejected: full-test `package_import_smoke` saw `VERSION_TAG=vv0.1.71.4` |
| v0.1.71.5 | Repair `VERSION_TAG` double-v normalization | Ensure `promptbranch_version.VERSION_TAG` is canonical `v0.1.71.5`, never `vv0.1.71.5` | `promptbranch_version.py`, focused version-surface tests, version metadata, repair/status docs | Docker behavior, project-registry behavior, release-set orchestration, adoption semantics | focused version-surface tests, package import smoke, source version consistency, control-surface test, compileall, ZIP hygiene | accepted_current |
| v0.1.72 | Project registry adoption/import ergonomics | Safely import existing repo-local current artifact records into the project-scoped registry through an explicit dry-run-capable command | `pb project import-current-registry`, registry import helpers, focused import/conflict tests, docs | release-set orchestration, dependency solving, automatic Project Source upload, automatic adoption, deployment behavior | focused project/repo import tests, control-surface test, compileall, ZIP hygiene, clean extraction validation | candidate |

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


## Repair definition — v0.1.71.5

```text
Release: v0.1.71.5
Base release: v0.1.71.4 candidate
Type: repair candidate
Slice advanced: no
Reason: v0.1.71.4 full-test import smoke observed `promptbranch_version.VERSION_TAG=vv0.1.71.4`; this double-prefix caused package import/version consistency failure even though other version surfaces normalized correctly.
In scope: compute `VERSION_TAG` through `version_tag()`, keep package version as bare PEP 440 text, normalize repeated leading `v` input, add regression tests proving `vv0.1.71.5` is rejected/not emitted, update repair/status docs and version metadata.
Out of scope: Docker behavior, project registry behavior, release-set orchestration, Project Source upload automation, artifact adoption semantics, deployment behavior.
Expected validation: focused promptbranch_version tests, package import smoke, source version consistency, project control-surface test, compileall, ZIP hygiene, clean extraction focused validation.
```


## Slice definition — v0.1.72 normal release

```text
Release: v0.1.72
Baseline: chatgpt_claudecode_workflow-2_v0.1.71.5.zip accepted/current with operator adoption evidence.
Type: normal candidate
Slice: Project registry adoption/import ergonomics
Goal: migrate existing repo-local `.pb_profile/promptbranch_artifacts.json` current records into the project-scoped registry explicitly, safely, and repeatably.
In scope: `pb project import-current-registry`, default import source from the joined repo's `.pb_profile`, optional `--from-profile-dir`, `--dry-run`, conflict detection, explicit `--replace`, project state updates for imported current records, focused tests, docs/status updates, version metadata.
Out of scope: release-set orchestration, cross-repo dependency solving, automatic Project Source upload, automatic artifact adoption, deployment behavior, Docker behavior, broad lifecycle rewrite.
Expected files: `promptbranch_project.py`, `promptbranch_cli.py`, `tests/test_promptbranch_project.py`, `docs/project/*`, `docs/release-v0.1.72.md`, `docs/promptbranch-multi-repo-projects.md`, version files.
Expected validation: project import focused tests, repo/project registry focused tests, project control-surface test, source version consistency, package import smoke, compileall, ZIP hygiene, clean extraction focused validation.
DoD movement: add DOD-021 for explicit project registry import ergonomics; mark done after focused validation passes.
Risk: importing current records can change project registry truth; dry-run and fail-closed conflict detection are mandatory.
Next step: package candidate ZIP and require operator install/test/adoption evidence before treating it as accepted/current.
```


## Slice definition — v0.1.73 normal release

```text
Release: v0.1.73
Baseline: chatgpt_claudecode_workflow-2_v0.1.72.zip accepted/current with operator adoption evidence.
Type: normal candidate
Slice: Canonical artifact naming and adopt compatibility
Goal: define one artifact filename grammar and make pb artifact adopt deterministic for multi-repo project baselines.
In scope: canonical <repo_id>_<version>.zip grammar, v-prefixed filename versions, extended numeric versions, v/non-v ZIP VERSION normalization, explicit --local-only adoption, Project Source adoption preserved, focused tests, docs, release/status metadata.
Out of scope: automatic historical ZIP rewriting, Project Source upload, release-set orchestration, dependency solving, runtime behavior, Docker/deployment changes.
Expected validation: focused artifact/adopt tests, repo doctor pattern tests, project control-surface test, source version consistency, package import smoke, compileall, ZIP hygiene, clean extraction validation.
DoD movement: add DOD-022 for canonical artifact naming and adopt compatibility.
Risk: adoption state mutation must remain explicit and fail closed for non-canonical names and conflicting adoption modes.
Next step: package candidate ZIP and require operator install/test/adoption evidence before treating it as accepted/current.
```

## Repair slice definition — v0.1.73.1

```text
Release: v0.1.73.1
Baseline: chatgpt_claudecode_workflow-2_v0.1.73.zip
Type: repair candidate
Slice: Canonical artifact adoption diagnostics and external-repo status semantics
Goal: Repair v0.1.73 adoption/current JSON semantics and ZIP hygiene diagnostics proven during candlecast multi-repo seeding.
In scope: source_verification object for local-only adoption, attempted_local_path diagnostics, external repo code-version relation fields, `.promptbranch-repo.json` portable identity hygiene validation, tests, repair note, project status docs.
Out of scope: normal v0.1.74 functionality, release-set orchestration, cross-repo dependency solving, Project Source upload changes, runtime/browser automation, Docker/deployment behavior, historical registry rewriting.
Expected validation: focused artifact/adopt/current/hygiene tests, project control-surface test, source version consistency, package import smoke, compileall, ZIP hygiene, clean extraction validation.
DoD movement: add DOD-023 for canonical adoption diagnostics and external-repo current-state reporting.
Risk: maintain backward-compatible fields while clarifying semantics so existing callers do not break unexpectedly.
Next step: package repair ZIP and require operator install/test/adoption evidence before treating it as accepted/current.
```

| v0.1.73.4 | Focused scheduler test isolation repair | Keep scheduler repair tests deterministic under real repo profiles | `tests/test_promptbranch_cli.py`, version/docs repair note | production behavior changes, v0.1.74 scope | focused scheduler/JSON-contract tests, release-control | candidate |


## Slice definition — v0.1.74 normal release

```text
Release: v0.1.74
Baseline: chatgpt_claudecode_workflow-2_v0.1.73.4.zip accepted/current with operator adoption evidence.
Type: normal candidate
Slice: Release validation suite coverage manifest
Goal: make release-control/full-test validation explicitly declare and run the focused regression groups that protected the v0.1.73.x repair line.
In scope: validation matrix doc, release-validation group metadata, full-test agent profile group execution, test-report group summary, release-control structured summary group summary, focused tests, release/status metadata.
Out of scope: browser automation behavior changes, Project Source semantic changes, artifact adoption/current behavior changes, multi-repo registry behavior changes, Docker/deployment behavior changes, unrelated pytest cleanup.
Expected files: `promptbranch_test_suite.py`, `promptbranch_test_report.py`, `chatgpt_claudecode_workflow_release_control.sh`, `tests/test_promptbranch_test_suite.py`, `tests/test_promptbranch_test_report.py`, `docs/project/*`, `docs/release-v0.1.74.md`, version files.
Expected validation: focused test-suite/report tests, artifact JSON contract tests, scheduler/source lifecycle tests, project/repo/control/version tests, compileall, ZIP hygiene, clean extraction validation, release-control before adoption.
DoD movement: add DOD-027 for explicit release-validation groups.
Risk: full release-control may take longer because focused pytest groups are no longer manual/optional.
Next step: package candidate ZIP and require operator install/test/adoption evidence before treating it as accepted/current.
```

## Slice definition — v0.1.74.2 repair

```text
Release: v0.1.74.2
Baseline: accepted/current v0.1.73.4 with v0.1.74/v0.1.74.1 intended release changes carried forward
Type: repair
Slice: Release-lifecycle plan test profile isolation
Goal: Keep synthetic release-lifecycle plan tests independent from ambient operator artifact registry state.
In scope: `tests/test_promptbranch_cli.py`, version surfaces, project status/release docs, repair note.
Out of scope: production release reconciliation behavior, Project Source semantics, artifact adoption/current semantics, scheduler/browser behavior, v0.1.75 scope.
Expected validation: focused release lifecycle plan tests, required release-validation groups, project/repo/control/version tests, compileall, ZIP hygiene, release-control.
DoD movement: DOD-029 added/done after focused validation; accepted/current verification remains pending.
Risk: low; test isolation only.
Next step: run release-control for v0.1.74.2 and adopt only after green evidence.
```

