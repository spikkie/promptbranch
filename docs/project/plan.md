# Project Plan

## Current baseline

```text
accepted/current baseline: chatgpt_claudecode_workflow-2_v0.1.76.zip
accepted checksum: 27030674c5af1b1d9d5199e638b55c2d3beed4b7df36175082e107992721d96f
active repair target: chatgpt_claudecode_workflow-2_v0.1.77.8.zip
next normal target after accepted repair: chatgpt_claudecode_workflow-2_v0.1.78.zip
release line: v0.1.x JSON orchestration / Promptbranch workflow control-plane hardening
```

## Plan summary

```text
Keep release slices narrow and KISS-first. v0.1.76 is the accepted/current baseline. v0.1.77 is the normal repo-loop compatibility-hardening slice, and v0.1.77.8 is a repair candidate that preserves that slice while making the Docker-service adapter accept and forward explicit per-call project URLs after v0.1.77.7 release-control still failed at `project_remove_cleanup`.
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
| v0.1.75 | KISS project/repo management command model | Use one repo-loop command/state model for one repo or many repos | `pb artifact current`, `pb project status`, project/repo inventory payloads, focused tests, status docs | release-set orchestration, dependency solving, automatic cross-repo adoption, browser behavior | focused project/repo tests, artifact-current regression tests, project control-surface test, compileall, ZIP hygiene | candidate |

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



## Slice definition — v0.1.74.3 repair

Release: v0.1.74.3  
Baseline: accepted/current v0.1.73.4 with v0.1.74/v0.1.74.1/v0.1.74.2 intended changes carried forward  
Type: repair

Goal: align the full integration source-mutation wait budget with the universal browser-operation scheduler wait budget.

In scope: replace the hard-coded 120s source-mutation wait in `promptbranch_full_integration_test.py` with the scheduler/profile-lock configuration surface and add focused regression coverage.

Out of scope: browser automation behavior changes, Project Source semantics, artifact adoption semantics, multi-repo behavior, Docker/deployment behavior, v0.1.75 scope.

Next step: run release-control for v0.1.74.3 and adopt only after green evidence.


## Slice definition — v0.1.75 normal release

```text
Release: v0.1.75
Baseline: chatgpt_claudecode_workflow-2_v0.1.74.3.zip accepted/current by operator baseline instruction.
Type: normal candidate
Slice: KISS project/repo management command model
Goal: make every project use the same repo-loop command and state shape, regardless of whether it has one repo or ten.
In scope: `pb artifact current --json`, `pb artifact current --all --json`, `pb artifact current --repo <repo> --json`, `pb project status --json`, project/repo inventory payloads, focused tests, release/status docs, version metadata.
Out of scope: release-set orchestration, dependency solving, automatic cross-repo adoption, Project Source upload changes, browser automation behavior, Docker/deployment behavior.
Expected files: `promptbranch_cli.py`, `tests/test_promptbranch_repos.py`, `tests/test_project_control_surface.py`, `tests/test_promptbranch_version.py`, `docs/project/*`, `docs/release-v0.1.75.md`, version files.
Expected validation: project/repo focused pytest, artifact-current regression tests, project control-surface pytest, Python compileall, ZIP hygiene, clean extraction focused validation.
DoD movement: add DOD-031 for KISS repo-loop management; mark done after focused validation passes.
Risk: joined-project `pb artifact current --json` returns the repo-loop payload shape; local scripts consuming old single-repo JSON may need updates.
Next step: package candidate ZIP and require operator install/test/adoption evidence before treating it as accepted/current.
```


## Slice definition — v0.1.76 normal release

```text
Release: v0.1.76
Baseline: chatgpt_claudecode_workflow-2_v0.1.75.zip accepted/current
Type: normal candidate
Slice: KISS repo-loop consumer cleanup for operator scripts and release-state checks
Goal: remove remaining old single-repo artifact-current payload assumptions from operator/release consumers.
In scope: release-control semantic checks, post-release validation semantic checks, lifecycle-status/human-summary artifact-current extraction, focused tests, docs/project updates, version metadata.
Out of scope: release-set orchestration, dependency solving, automatic cross-repo adoption, Project Source upload behavior, browser automation behavior, Docker/deployment behavior.
Expected files: promptbranch_cli.py, chatgpt_claudecode_workflow_release_control.sh, scripts/post-release-validation.sh, tests/test_promptbranch_shell_scripts.py, tests/test_post_release_validation.py, docs/project/*, docs/release-v0.1.76.md, version files.
Expected validation: focused artifact-current tests, release-control/post-release semantic guard tests, project/repo/control/version tests, bash syntax checks, compileall, ZIP hygiene, clean extraction validation.
DoD movement: add DOD-032 for repo-loop consumers.
Risk: scripts outside this repo may still consume legacy top-level artifact-current JSON.
Next step: package candidate ZIP and require operator install/test/adoption evidence before treating it as accepted/current.
```


## Slice definition — v0.1.77 normal release

```text
Release: v0.1.77
Baseline: chatgpt_claudecode_workflow-2_v0.1.76.zip accepted/current
Type: normal candidate
Slice: Repo-loop compatibility hardening and operator migration guardrails
Goal: make remaining artifact-current compatibility behavior explicit and keep normal operator/release paths on repo-loop sections.
In scope: docs/project accepted-current update for v0.1.76, normalized artifact-current section helper hardening, release/dev/lifecycle helper consumers, parallel ask baseline safety, repo-loop/legacy fallback tests, migration note, version metadata.
Out of scope: registry storage changes, adoption semantics changes, Project Source upload behavior, dependency solving between repos, automatic multi-repo adoption, release-set orchestration, browser automation, Docker/deployment behavior.
Expected files: promptbranch_cli.py, promptbranch_parallel_ask.py, tests/test_promptbranch_cli.py, tests/test_promptbranch_parallel_ask.py, docs/project/*, docs/release-v0.1.77.md, version files.
Expected validation: focused artifact-current/repo-loop compatibility tests, parallel ask baseline-safety tests, project control-surface tests, version tests, compileall, ZIP hygiene, clean extraction validation.
DoD movement: add DOD-033 for artifact-current compatibility surface hardening.
Risk: scripts outside this repo may still consume legacy top-level artifact-current JSON.
Next step: package candidate ZIP and require operator install/test/adoption evidence before treating it as accepted/current.
```


## Slice definition — v0.1.77.1 repair release

```text
Release: v0.1.77.1
Baseline: chatgpt_claudecode_workflow-2_v0.1.76.zip plus v0.1.77 intended slice content
Type: repair
Slice: Temporary project create/remove lifecycle hardening
Goal: Repair v0.1.77 validation defects without advancing the repo-loop compatibility slice.
In scope: create-project disabled-submit refill/recheck, cleanup absence verification after sidebar-not-found, focused regression tests, repair note, project control-surface updates.
Out of scope: new repo-loop behavior, registry/adoption changes, Project Source upload behavior, release-set orchestration, browser service API expansion beyond diagnostics/robustness.
Expected files: promptbranch_browser_auth/client.py, chatgpt_browser_auth/client.py, promptbranch_full_integration_test.py, focused tests, docs/repair-v0.1.77.1.md, docs/project/*, version files.
Expected validation: focused browser lifecycle tests, project control-surface tests, version tests, bash syntax, compileall, ZIP hygiene, clean extraction validation, then full release-control by operator.
DoD movement: DOD-034 done after focused validation; no normal slice advanced.
Risk: ChatGPT UI behavior remains live/external and can still produce non-deterministic latency, but cleanup must no longer hide leaked projects.
Next step: package v0.1.77.1 and run release-control.
```


## Repair definition — v0.1.77.2

```text
Release: v0.1.77.2
Base release: v0.1.77.1
Type: repair candidate
Slice advanced: no
Reason: v0.1.77.1 failed release-control because cleanup stopped after the first sidebar-not-found event even though exact-name resolve still found the temporary project, and a required release-validation group timed out without useful diagnostics.
In scope: retry/retarget temporary project cleanup when absence is not verified, verify success when project name is known, isolate release-validation pytest subprocesses from ambient plugins, focused tests, repair/status docs, version metadata.
Out of scope: repo-loop semantics, registry/adoption semantics, Project Source upload behavior, release-set orchestration, Docker/deployment behavior, new normal slice work.
Expected validation: focused cleanup tests, release-validation group tests, project control-surface test, version tests, compileall, ZIP hygiene, clean extraction validation.
Next step: run release-control for v0.1.77.2 and adopt only after pb artifact current --all --json confirms alignment.
```


## Repair definition — v0.1.77.3

```text
Release: v0.1.77.3
Baseline: accepted/current v0.1.76 plus intended v0.1.77/v0.1.77.1/v0.1.77.2 repair line content
Type: repair
Slice: hidden temporary project removal hardening
Goal: When cleanup can resolve the exact temporary project by name but cannot find it in the normal sidebar, open the More-projects surface before failing.
In scope: project removal fallback, focused tests, repair docs/status.
Out of scope: repo-loop semantics, registry/adoption semantics, Project Source upload behavior, release-set orchestration, normal feature work.
Expected validation: focused project removal tests, focused cleanup tests, control-surface/version tests, compileall, ZIP hygiene, full release-control before adoption.
DoD movement: DOD-036 added/done after focused validation.
Risk: live ChatGPT rate-limit pressure may still require rerun or manual cleanup for already leaked projects.
Next step: run release-control for v0.1.77.3 and adopt only after pb artifact current --all --json confirms alignment.
```


## Repair definition — v0.1.77.4

```text
Release: v0.1.77.4
Baseline: accepted/current v0.1.76 plus intended v0.1.77/v0.1.77.1/v0.1.77.2/v0.1.77.3 repair-line content
Type: repair candidate
Slice advanced: no
Reason: v0.1.77.3 failed release-control because exact-name cleanup still found the temporary project while ChatGPT rate-limit telemetry showed backend 429/modal pressure.
In scope: rate-limit-aware cleanup retry delay, extended cleanup attempts, longer direct project details-menu wait, final rate-limit modal clearance before sidebar-not-found failure, focused tests, repair/status docs, version metadata.
Out of scope: repo-loop semantics, registry/adoption semantics, Project Source upload behavior, release-set orchestration, Docker/deployment behavior, new normal slice work.
Expected validation: focused cleanup/remove tests, project control-surface test, version tests, compileall, ZIP hygiene, clean extraction validation.
Next step: run release-control for v0.1.77.5 and adopt only after pb artifact current --all --json confirms alignment.
```


## Repair definition — v0.1.77.5

```text
Release: v0.1.77.5
Baseline: accepted/current v0.1.76 plus intended v0.1.77 repair-line content
Type: repair
Slice: Required root `.gitignore` packaging repair
Goal: Restore required root `.gitignore` in the ZIP so release-control import validation can proceed.
In scope: `.gitignore`, version surfaces, repair docs/status updates, focused validation.
Out of scope: normal release scope, repo-loop semantics, registry/adoption semantics, Project Source upload behavior.
Expected validation: import-plan root-file check, focused version/control tests, compileall, bash syntax, ZIP hygiene.
DoD movement: DOD-038 done.
Risk: low; packaging surface only.
Next step: run release-control for v0.1.77.5 and adopt only after pb artifact current --all --json confirms alignment.
```

## Repair definition — v0.1.77.6

```text
Release: v0.1.77.6
Baseline: accepted/current v0.1.76 plus intended v0.1.77 repair-line content
Type: repair
Slice: Project-page delete-menu fallback and bounded scheduler validation timeout
Reason: v0.1.77.5 failed release-control because the temporary project stayed exact-name resolvable while sidebar removal could not find it, and the scheduler validation group timed out at 600 seconds after browser failure.
Scope: widen project-page delete-menu selectors; cap browser_scheduler_source_lifecycle release-validation timeout at 120 seconds.
Out of scope: repo-loop semantics, registry/adoption semantics, Project Source upload behavior, Docker/deployment behavior, normal v0.1.78 scope.
Expected validation: focused project removal selector tests, release-validation timeout test, project control-surface/version tests, compileall, ZIP hygiene, full release-control.
DoD movement: DOD-039 done after focused validation.
Next step: run release-control for v0.1.77.6 and adopt only after pb artifact current --all --json confirms alignment.
```



## Repair definition — v0.1.77.7

```text
Release: v0.1.77.7
Baseline: accepted/current v0.1.76 plus intended v0.1.77 repair-line content
Type: repair
Slice: explicit resolved-project-url cleanup retry
Goal: ensure temporary project cleanup retries remove/resolve requests against the exact resolved project URL instead of only mutating a client attribute.
In scope: promptbranch_full_integration_test.py cleanup retry plumbing, focused cleanup regression test, repair/status docs, version metadata.
Out of scope: repo-loop semantics, registry/adoption semantics, Project Source upload behavior, release-set orchestration, Docker/deployment behavior, normal release scope.
Expected files: promptbranch_full_integration_test.py, tests/test_full_integration_harness.py, docs/repair-v0.1.77.7.md, docs/project/*, version surfaces.
Expected validation: focused cleanup retarget tests, project control-surface tests, version tests, compileall, bash syntax, ZIP hygiene, clean extraction validation, then full release-control by operator.
DoD movement: DOD-040 done after focused validation.
Risk: ChatGPT UI may still refuse deletion if no delete action is exposed, but cleanup must remain fail-closed.
Next step: run release-control for v0.1.77.7 and adopt only after pb artifact current --all --json confirms alignment.
```


## Repair definition — v0.1.77.8

```text
Release: v0.1.77.8
Baseline: accepted/current v0.1.76 plus intended v0.1.77 repair-line content
Type: repair
Slice: Docker-service cleanup retarget accepts explicit project URL
Goal: ensure retargeted temporary project cleanup sends the exact resolved project URL through Docker-service remove/resolve calls.
In scope: DockerServiceAdapter remove_project/resolve_project optional project_url support, focused cleanup adapter regression test, repair/status docs, version metadata.
Out of scope: repo-loop semantics, registry/adoption semantics, Project Source upload behavior, release-set orchestration, Docker/deployment behavior, normal release scope.
Expected files: promptbranch_full_integration_test.py, tests/test_full_integration_harness.py, docs/repair-v0.1.77.8.md, docs/project/*, version surfaces.
Expected validation: focused DockerServiceAdapter cleanup test, project control-surface tests, version tests, compileall, bash syntax, ZIP hygiene, clean extraction validation, then full release-control by operator.
DoD movement: DOD-041 done after focused validation.
Risk: ChatGPT UI may still refuse deletion even when called with the exact resolved project URL, but cleanup remains fail-closed.
Next step: run release-control for v0.1.77.8 and adopt only after pb artifact current --all --json confirms alignment.
```
