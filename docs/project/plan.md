# Project Plan

## Current baseline

```text
accepted/current baseline: chatgpt_claudecode_workflow-2_v0.1.76.zip
accepted checksum: 27030674c5af1b1d9d5199e638b55c2d3beed4b7df36175082e107992721d96f
active repair target: chatgpt_claudecode_workflow-2_v0.1.77.11.zip
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
## Repair slice — v0.1.77.9

```text
Release: v0.1.77.9
Baseline: accepted/current v0.1.76 plus intended v0.1.77 repair-line content
Type: repair
Slice: source-save stale-inflight proof and cleanup project-name forwarding
Goal: unblock v0.1.77 release-control by making text-source stale-inflight handling depend on post-refresh persistence proof and by forwarding project_name with exact project_url through cleanup removal.
In scope: source-save quiet diagnostic handling, post-refresh persistence proof boundary, Docker/service/browser cleanup request forwarding, focused regression tests.
Out of scope: normal release scope, repo-loop semantics, registry/adoption semantics, Project Source upload behavior beyond validation proof, release-set orchestration.
Expected validation: focused source-save quiet tests, cleanup/remove tests, service-client request tests, project control-surface tests, version tests, compileall, ZIP hygiene.
DoD movement: DOD-042 done.
Risk: live ChatGPT UI may still expose no removable state for leaked projects; fail-closed cleanup remains required.
Next step: run release-control for v0.1.77.9.
```


## Repair definition — v0.1.77.10

```text
Release: v0.1.77.10
Baseline: accepted/current v0.1.76 plus intended v0.1.77 repair-line content
Type: repair
Slice: version-pinned Docker service image selection
Goal: Prevent release-control from validating against a stale Docker service image after install.
In scope: release-control Docker Compose image pinning, service start image pinning, focused shell-script tests, repair docs.
Out of scope: repo-loop semantics, registry/adoption semantics, Project Source upload semantics, browser cleanup semantics, Docker deployment architecture changes.
Expected files: chatgpt_claudecode_workflow_release_control.sh, run_chatgpt_service.sh, run_chatgpt_service_dev.sh, tests/test_promptbranch_shell_scripts.py, docs/repair-v0.1.77.10.md, docs/project/*, version surfaces.
Expected validation: focused shell-script tests, project control/version tests, compileall, bash syntax, ZIP hygiene, release import-plan.
DoD movement: DOD-043 done after focused validation.
Risk: A deliberately custom image override now requires PROMPTBRANCH_ALLOW_SERVICE_IMAGE_OVERRIDE=1 during release-control.
Next step: run release-control for v0.1.77.10 and adopt only after pb artifact current --all --json confirms alignment.
```


## Repair definition — v0.1.77.11

```text
Release: v0.1.77.11
Baseline: accepted/current v0.1.76 plus intended v0.1.77 repair-line content
Type: repair
Slice: name-only non-anchor project cleanup fallback
Goal: remove temporary projects when ChatGPT renders the project row as a button/menu item instead of an anchor row.
In scope: promptbranch_browser_auth/client.py, tests/test_project_resolve.py, docs/repair-v0.1.77.11.md, docs/project/*, version surfaces.
Out of scope: normal slice advancement, release-line advancement, repo-loop changes, registry/adoption changes, Docker service image changes.
Expected validation: focused project resolve/remove tests, project control/version tests, compileall, bash syntax, ZIP hygiene, then full release-control by operator.
DoD movement: DOD-044 done after focused validation.
Risk: live ChatGPT UI may still hide delete controls under rate-limit/sidebar state; cleanup must remain fail-closed.
Next step: run release-control for v0.1.77.11 and adopt only after pb artifact current --all --json confirms alignment.
```


## Slice definition — v0.1.78 normal release

```text
Release: v0.1.78
Baseline: chatgpt_claudecode_workflow-2_v0.1.77.11.zip accepted/current with operator adoption evidence.
Type: normal candidate
Slice: AG-001 — Deterministic Artifact Guardian Guard
Goal: add deterministic .artifact-guardian.yml policy loading and pb artifact guard ZIP validation so structurally invalid release ZIPs fail before lifecycle install or operator/assistant handoff.
In scope: .artifact-guardian.yml, policy loader, ZIP inspector, pb artifact guard, strict JSON output, required/forbidden/wrapper/nested/version/name/executable checks, missing .gitignore regression test, project docs/status updates.
Out of scope: pb artifact build integration, healing, agent orchestration, lifecycle integration, assistant-side handoff enforcement, source adoption, accepted/current changes, deployment validation, runtime correctness validation, k8s-game docs/schemas/state machines/drawio roadmap.
Expected validation: tests/test_artifact_guardian.py, project control/version tests, compileall, bash syntax, ZIP hygiene, clean extraction validation, release-control before adoption.
DoD movement: add DOD-045 for deterministic Artifact Guardian guard.
Risk: guard_passed must remain candidate-structure evidence only and must not imply accepted/current.
Next step: package candidate ZIP and require operator install/test/adoption evidence before treating it as accepted/current.
```

## Reserved slice definition — v0.1.79 normal release

```text
Release: v0.1.79
Baseline: accepted/current v0.1.78 after adoption evidence.
Type: normal candidate
Slice: Rebaselined JSON orchestration / k8s-game MVP foundation
Goal: add documentation, schemas, examples, state-machine definitions, and Draw.io roadmap documents for the k8s-game MVP foundation after AG-001 protects release ZIP handoff.
Out of scope for v0.1.79 until started: game runtime, Dockerfile, Kubernetes manifests, deployment, write-capable orchestration.
```


## Slice definition — v0.1.78.1 repair release

```text
Release: v0.1.78.1
Baseline: v0.1.78 candidate ZIP
Type: repair
Slice: Project Source mutation transaction hardening
Goal: Repair the v0.1.78 release-control failure where file Project Source add saw commit evidence but refreshed persistence was not verified.
In scope: explicit source mutation transaction classification, extended post-commit file-source readback, failed-step reporting for returned `{ok:false}` step results, focused regression tests, repair note/status updates.
Out of scope: AG-001 guard behavior changes, build integration, heal, agent orchestration, lifecycle integration, assistant-side handoff, adoption/current changes, k8s-game foundation.
Expected validation: focused Project Source transaction tests, integration harness step-result tests, project control/version tests, compileall, bash syntax, ZIP hygiene, release-control from ZIP.
DoD movement: DOD-046.
Risk: live ChatGPT file-source indexing may still be delayed beyond the extended readback window; final state remains fail-closed.
Next step: run release-control on v0.1.78.1 and adopt only with pb artifact current alignment evidence.
```


## Slice definition — v0.1.78.2 repair release

```text
Release: v0.1.78.2
Baseline: v0.1.78.1 candidate ZIP
Type: repair
Slice: Project deletion safety freeze
Goal: Freeze ChatGPT Project deletion after live-log evidence showed Promptbranch can execute real project delete flows.
In scope: canonical project_delete_disabled payload, /v1/projects/remove pre-service block, public automation/browser remove_project blocks, full-integration cleanup skip for delete-frozen payloads, focused delete-safety tests, repair/status docs.
Out of scope: future secure delete protocol design, any actual ChatGPT Project deletion, Project Source removal behavior changes, AG-001 guard behavior changes, adoption/current changes, k8s-game foundation.
Expected validation: tests/test_project_delete_safety.py, project control/version tests, compileall, bash syntax, ZIP hygiene, release-control before adoption.
DoD movement: DOD-047.
Risk: temporary integration-test projects can be retained intentionally until a safe cleanup protocol exists. This is safer than accidental deletion of real projects.
Next step: run release-control on v0.1.78.2 and adopt only with pb artifact current alignment evidence.
```


## Slice definition — v0.1.78.2.1 repair release

```text
Release: v0.1.78.2.1
Baseline: v0.1.78.2 candidate ZIP
Type: repair
Slice: package delete-safety helper module
Goal: Fix v0.1.78.2 release-control import failure by installing promptbranch_project_delete_safety as a setuptools py-module.
In scope: pyproject.toml py-modules, version surfaces, package/import-focused validation, repair/status docs.
Out of scope: secure delete protocol, any actual ChatGPT Project deletion, Project Source removal behavior changes, AG-001 guard behavior changes, adoption/current changes, k8s-game foundation.
Expected validation: package/import tests, tests/test_project_delete_safety.py, project control/version tests, compileall, bash syntax, ZIP hygiene, release-control before adoption.
DoD movement: DOD-047 preserved; no new functional DoD.
Risk: if future top-level helper modules are added, packaging metadata must be updated or replaced with package-local modules to avoid repeat import failures.
Next step: run release-control on v0.1.78.2.1 and adopt only with pb artifact current alignment evidence.
```


## Slice definition — v0.1.78.2.2 repair release

```text
Release: v0.1.78.2.2
Baseline: v0.1.78.2.1 candidate ZIP
Type: repair
Slice: Release-control multi-segment repair-version compatibility
Goal: Fix v0.1.78.2.1 release-control rejection of nested repair versions such as v0.1.78.2.1.
In scope: release-control normalize_version, artifact prefix extraction, post-release-validation normalize_version, artifact candidate schema version grammar, focused shell-script regression test, repair/status docs.
Out of scope: secure delete protocol, any actual ChatGPT Project deletion, Project Source removal behavior changes, AG-001 guard behavior changes, adoption/current changes, k8s-game foundation.
Expected validation: tests/test_promptbranch_shell_scripts.py::test_release_control_accepts_multi_segment_repair_versions, project control/version tests, protocol schema JSON tests, compileall, bash syntax, ZIP hygiene, release-control before adoption.
DoD movement: DOD-048 added/done; DOD-047 preserved.
Risk: version grammar should stay numeric-only and fail closed for labels or ambiguous strings.
Next step: run release-control on v0.1.78.2.2 and adopt only with pb artifact current alignment evidence.
```

## Slice definition — v0.1.78.2.3 repair release

```text
Release: v0.1.78.2.3
Baseline: v0.1.78.2.2 candidate ZIP
Type: repair
Slice: Retained quarantine project for delete-frozen release tests
Goal: Stop release-control full tests from creating a new unique ChatGPT Project on every run while project deletion is frozen.
In scope: release-control pb test full invocation, retained quarantine project default, focused shell-script regression tests, repair/status docs.
Out of scope: secure delete protocol, actual ChatGPT Project deletion, deleting existing leaked itest projects, Project Source removal behavior changes, AG-001 guard behavior changes, adoption/current changes, k8s-game foundation.
Expected validation: focused shell-script tests proving pb test full uses --project-name itest-promptbranch-retained-delete-frozen --keep-project, project control/version tests, compileall, bash syntax, ZIP hygiene, release-control before adoption.
DoD movement: DOD-049 added/done; DOD-047 and DOD-048 preserved.
Risk: the retained quarantine project can accumulate test chats/sources over time; source add/remove checks must continue to use unique source names and remove sources after each run.
Next step: run release-control on v0.1.78.2.3 and adopt only with pb artifact current alignment evidence.
```



## Slice definition — v0.1.78.2.4 repair release

Release: v0.1.78.2.4
Type: repair
Slice: Delete-frozen live-test profile alignment and one-command all-tests report

Scope:
- Make `pb test ask-live`, `pb test visual-artifact-roundtrip`, and `pb test release-live` use/reuse the retained delete-frozen project by default.
- Force keep-project semantics for those live profiles while ChatGPT Project deletion remains frozen.
- Remove stale operator/help wording that implies automatic temporary project deletion.
- Add release-control `--run-all-tests` to run the full operator validation stack in one command.
- Continue after individual test failures and write a final machine-readable GO/FIX report.

Out of scope:
- Secure delete protocol.
- Any ChatGPT Project deletion attempt.
- Project Source removal behavior changes.
- Artifact adoption/current mutation.
- v0.1.79/k8s-game foundation work.

Expected validation: focused CLI/parser/live-test tests, release-control all-tests shell test, project control/version tests, compileall, bash syntax, package import smoke, artifact guard, then release-control from ZIP before adoption.


## Slice definition — v0.1.78.2.5 repair release

Release: v0.1.78.2.5
Type: repair
Slice: Run-all verdict accuracy and live-profile auth preflight

Scope:
- Add live-profile preflight to release-control `--run-all-tests`.
- Run `ask-live`, `visual-artifact-roundtrip`, and `release-live` through a refreshed `release-live` profile-pool slot seeded from `.pb_profile_local_debug`.
- Include `full_direct` and `full_localhost` as first-class rows in the all-tests summary.
- Parse the top-level Promptbranch JSON result for each step instead of nested JSON fragments.
- Continue after failures and emit final GO/FIX verdict.
- Ignore `.pb_profile_local_debug_pools/` in `.gitignore`.

Out of scope:
- Secure delete protocol.
- ChatGPT Project deletion.
- Project Source removal behavior changes.
- Adoption/current mutation.
- v0.1.79/k8s-game foundation work.

Expected validation: focused shell-script/parser/CLI tests, project control/version/delete-safety tests, compileall, bash syntax, package import smoke, artifact guard, then release-control `--run-all-tests` from ZIP before adoption.

## Slice definition — v0.1.78.2.6 repair release

Release: v0.1.78.2.6

Goal: prevent Docker tag/content mismatch without forcing every release build to use `--no-cache`.

Scope:

- Pass target version and artifact SHA as Docker build args.
- Add Dockerfile build-context version assertion.
- Add release-control host build-context version assertion.
- Add release-control built-image content probe before compose up.
- Add release-control running-container content probe before healthz acceptance.
- Keep no-cache as one bounded fallback.
- Preserve project deletion freeze and run-all behavior.

Out of scope:

- Secure project deletion protocol.
- Project Source removal changes.
- Adoption/current mutation.
- v0.1.79/k8s-game work.


## Slice definition — v0.1.78.2.7 repair release

Release: v0.1.78.2.7

Goal: repair the embedded Python syntax defect in the Docker provenance probe JSON writer introduced by v0.1.78.2.6 while preserving the cache/provenance guard behavior.

In scope:

- Fix newline string literal handling in Docker image/container probe JSON writers.
- Add a focused regression check.
- Keep project deletion frozen and live-test retained project defaults intact.

Out of scope:

- Secure project delete protocol.
- Project Source behavior changes.
- Normal v0.1.79 work.

| v0.1.78.2.8 | repair | Docker pyproject probe quoting repair | candidate | focused Docker probe quoting/version/delete-safety/project-control tests, compileall, bash syntax, ZIP hygiene before operator release-control | DOD-054 done; DOD-047/DOD-050/DOD-051/DOD-052/DOD-053 preserved | pending |


## Slice definition — v0.1.78.2.9 repair release

Release: v0.1.78.2.9

Goal: repair the Docker image/container pyproject probe so it is safe under `set -u` and does not expand shell positional parameter `$2`.

In scope:

- Replace awk `$2` pyproject extraction in Docker image/content probes with a shell-safe `grep | head | cut` reader.
- Add a focused regression check that rejects the old awk-dollar probe form.
- Preserve Docker provenance checks, bounded no-cache fallback, retained live-test project behavior, and project deletion freeze.

Out of scope:

- Secure project delete protocol.
- Project Source behavior changes.
- Adoption/current mutation.
- v0.1.79/k8s-game work.

## Slice definition — v0.1.78.2.10 repair release

Release: v0.1.78.2.10

Goal: make ChatGPT conversation-history 429 / "Too many requests" backpressure recoverable in `--run-all-tests` by acknowledging the modal in browser code, waiting for cooldown, and retrying the failed release-control step once before declaring FIX.

Non-goals: project deletion, secure delete, Project Source behavior changes, artifact adoption mutation, v0.1.79 work.

## Slice definition — v0.1.78.2.11 repair release

Release: v0.1.78.2.11

Goal: repair `--run-all-tests` so release-control preserves the live seed profile across candidate install and only retries failed steps when strict ChatGPT rate-limit evidence is present.

In scope:

- Preserve `.pb_profile_local_debug/` during ZIP import.
- Keep `.pb_profile_local_debug_pools/` disposable.
- Validate and sanitize the seed profile before live browser steps.
- Replace broad text matching with strict rate-limit evidence checks.
- Preserve Docker provenance and project deletion freeze.

Out of scope:

- Secure project deletion protocol.
- Project Source behavior changes.
- Adoption/current mutation.
- v0.1.79/k8s-game work.

## Slice definition — v0.1.78.2.12 repair release

Release: v0.1.78.2.12

Goal: repair the text Project Source add path after `v0.1.78.2.11` showed `ui_trigger_not_observed_not_verified_present` for the supported Text input source kind.

In scope:

- Verify that the text-source primary save click starts an observed save request.
- Apply bounded fallback triggers when no save request is observed.
- Keep `.pb_profile_local_debug/` as the operator-authenticated live seed and `.pb_profile_local_debug_pools/` disposable.
- Preserve Docker provenance, strict rate-limit detection, and project deletion freeze.

Out of scope:

- Secure project deletion protocol.
- Project Source removal changes.
- Adoption/current mutation.
- v0.1.79/k8s-game work.


## Slice definition — v0.1.78.2.15 repair release

Release: v0.1.78.2.15

Goal: repair Project Source add timeout false-negatives where upload/commit succeeds but post-refresh verification waits on unrelated conversation-history 429 cooldown until the CLI times out.

In scope:

- Keep 429/modal telemetry and acknowledgement.
- Skip persisted conversation-history cooldown for Project Source add/list/remove/capability operation startup.
- Skip persisted conversation-history cooldown after modal clear during Project Source persistence refresh.
- Preserve the cooldown for actual conversation-history operations.
- Add focused regression tests.

Out of scope:

- Secure project deletion protocol.
- Project Source overwrite/remove containment changes beyond preserving v0.1.78.2.14.
- Artifact adoption/current mutation.
- v0.1.79/k8s-game work.

## Slice definition — v0.1.78.2.20.8.3 repair release

Release: v0.1.78.2.20.8.3

Goal: repair the remaining focused fresh-project source-add/cleanup validation issues without changing source-add semantics.

In scope:

- Normalize slugged same-run ephemeral Project ids for cleanup validation.
- Preserve strict `itest-promptbranch-*` same-run cleanup guards.
- Extend bounded post-commit source-surface recovery to text-source commits with stale inflight state.
- Preserve prompt-file attachment behavior and broad Project deletion freeze.

Out of scope:

- Normal `v0.1.79` work.
- Broad Project deletion or user-project deletion.
- Artifact adoption/current mutation.
- Project Source success semantics changes.

## Slice definition — v0.1.78.2.20.8.4 repair release

Release: v0.1.78.2.20.8.4

Goal: repair the unsafe same-run ephemeral Project deletion exception introduced by v0.1.78.2.20.8.3 and restore an immutable no-delete invariant for every ChatGPT Project path.

In scope:

- Block all Project remove/delete requests at API, service, browser-client, and private browser-operation layers.
- Make full-integration cleanup record retained-project/delete-frozen status without calling any remove service.
- Preserve same-run identity fields as diagnostic-only evidence.
- Add regression tests proving `allow_ephemeral_test_cleanup=True` cannot authorize deletion.
- Preserve v0.1.78.2.20.8.3 text-source post-commit recovery behavior.

Out of scope:

- Secure project delete protocol.
- Project Source semantic changes beyond preserving the prior text-source recovery.
- Artifact adoption/current mutation.
- Normal v0.1.79 work.

## Slice definition — v0.1.78.2.20.8.5 repair release

Release: v0.1.78.2.20.8.5

Scope: repair-only cleanup-policy evidence label consistency on top of `v0.1.78.2.20.8.4`.

In scope:

- Remove the stale top-level `cleanup_policy="same_run_ephemeral_cleanup"` full-integration summary label.
- Ensure retained-project cleanup evidence reports `no_project_delete_until_secure_protocol`.
- Preserve the immutable no-delete invariant from `v0.1.78.2.20.8.4`.

Out of scope:

- Project deletion behavior changes.
- Secure delete protocol design or implementation.
- Project Source add/remove behavior changes.
- Artifact adoption/current changes.
- Normal `v0.1.79` scope.

## Slice definition — v0.1.78.2.20.8.6 repair release

Release: v0.1.78.2.20.8.6

Scope: repair-only joined-repo state authority consistency on top of `v0.1.78.2.20.8.5`.

In scope:

- Make backend state reads use the project-aware state store for joined repos.
- Preserve browser profile resolution separately from workflow state resolution.
- Preserve explicit `--profile-dir` override behavior.
- Add focused regression tests for project-scoped default state and explicit profile override.
- Preserve the immutable no-delete invariant and cleanup-policy evidence consistency.

Out of scope:

- Project deletion behavior changes.
- Secure delete protocol design or implementation.
- Project Source add/remove behavior changes.
- Artifact adoption/current changes.
- Normal `v0.1.79` scope.

## Slice definition — v0.1.78.2.20.8.7 repair release

Release: v0.1.78.2.20.8.7

Scope: repair-only plain-text response-wait diagnostic bookkeeping on top of `v0.1.78.2.20.8.6`.

In scope:

- Initialize `response_wait_breakdown` in `_wait_and_get_response()` before diagnostic/deadline branches can write to it.
- Preserve existing plain-text answer completion predicates and freshness/idle behavior.
- Add focused regression coverage for the debug artifact skipped due to deadline path.
- Preserve joined-repo state authority consistency and immutable Project deletion freeze.

Out of scope:

- Degraded completion when the answer text is stable but the stop button remains visible.
- Project deletion behavior changes.
- Secure delete protocol design or implementation.
- Project Source add/remove behavior changes.
- Artifact adoption/current changes.
- Normal `v0.1.79` scope.

## Slice definition — v0.1.78.2.20.8.8 repair release

Release: v0.1.78.2.20.8.8

Scope: repair-only localhost Project Source add stale-inflight diagnostic timeout alignment on top of `v0.1.78.2.20.8.7`.

In scope:

- Make Docker-service Project Source add client requests wait long enough to receive the service-side post-commit persistence/recovery result.
- Keep `commit_seen_with_stale_inflight_not_verified_present` and `post_commit_source_surface_not_refreshed` release-blocking and operator-review-required.
- Add a retained-project `pb src list --json` diagnostic after the specific post-commit source-surface failure.
- Add focused regression coverage for request-timeout override, source-mutation timeout floor, post-failure source-list diagnostics, and stale-inflight release-blocking payload fields.
- Preserve joined-repo state authority consistency, plain-text response wait diagnostics, and immutable Project deletion freeze.

Out of scope:

- Treating ambiguous source-add persistence as success.
- Increasing or relaxing Project Source success criteria.
- Project deletion behavior changes.
- Secure delete protocol design or implementation.
- Artifact adoption/current changes.
- Normal `v0.1.79` scope.

## Slice definition — v0.1.79 normal MVP release

Release: v0.1.79

Baseline: accepted/current `chatgpt_claudecode_workflow-2_v0.1.78.2.20.8.8.zip`.

Goal: resume the normal JSON orchestration MVP line with a small event-intake foundation that lets Promptbranch validate proposal-only orchestration JSON before any workflow state can be trusted.

In scope:

- Add `promptbranch.orchestration.event_intake` schema and one committed proposal fixture.
- Add a read-only validator for event-intake JSON.
- Expose the validator as `pb orchestration validate-event`.
- Keep event intake proposal-only: no runtime state write, no Project Source mutation, no artifact adoption, no deployment, and no model execution.
- Add focused tests for valid examples, mutating authority rejection, repo-relative path rejection, and baseline/target sanity.
- Update project control-surface docs.

Out of scope:

- k8s-game implementation or deployment.
- Generic orchestration engine/runtime.
- Accepted-event ledger mutation.
- Autonomous repository edits.
- Project Source overwrite/remove behavior.
- Artifact adoption/current mutation.
- Project deletion behavior or secure delete protocol.


## Slice definition — v0.1.80 normal MVP release

Release: v0.1.80

Name: Accepted-event validation foundation

Baseline: chatgpt_claudecode_workflow-2_v0.1.79.zip

Scope:

- Expose `pb orchestration validate-accepted-event --json` as a first-class read-only CLI command.
- Validate committed G0-G6 accepted-event fixtures through the same CLI surface operators use.
- Require accepted-event fixtures to bind to explicit accepted/current baseline artifact/source refs and canonical versions.
- Preserve accepted-event fixture-only status: no accepted ledger writes, no Project Source mutation, no artifact adoption, no deployment, and no model execution.
- Keep the v0.1.79 event-intake validator behavior unchanged.

Out of scope:

- Accepted-event ledger write path.
- Proposal promotion or `accept-event --write`.
- Runtime orchestration engine.
- k8s-game implementation/deployment.
- Project Source mutation changes.
- Artifact adoption/current mutation beyond normal release-control adoption.

DoD target: DOD-083.

## Slice definition — v0.1.81 focused working slice

Release: v0.1.81

Name: Accepted-event dry-run promotion foundation

Baseline context: `v0.1.80` focused working candidate built from accepted/current `chatgpt_claudecode_workflow-2_v0.1.79.zip`. Accepted/current remains `v0.1.79` until a later full promotion/adoption gate.

Scope:

- Add `pb orchestration accept-event --dry-run --json`.
- Reuse the installed-module accepted-event validator.
- Default to committed G0-G6 accepted-event fixtures when no explicit paths are passed.
- Return a deterministic preview of acceptable future accepted-event ledger records.
- Fail closed when validation rejects the accepted-event input.
- Preserve no-mutation authority: no accepted state write, no Project Source mutation, no artifact adoption, no deployment, and no model execution.

Out of scope:

- Accepted-event ledger write path.
- `accept-event --write`.
- Proposal/event-intake promotion into accepted-event JSON.
- Runtime orchestration engine.
- k8s-game implementation/deployment.
- Project Source mutation changes.
- Artifact adoption/current mutation beyond later release-control adoption.

DoD target: DOD-084.

## Slice definition — v0.1.82 focused working slice

Release: v0.1.82

Name: Accepted-event dry-run explicit input support

Baseline context: `v0.1.81` focused working candidate built on the `v0.1.80` focused candidate chain. Accepted/current remains `chatgpt_claudecode_workflow-2_v0.1.79.zip` until a later full promotion/adoption gate.

Scope:

- Support `pb orchestration accept-event --dry-run --json <accepted-event-file>` as a first-class explicit input path.
- Return a single accepted-event preview for a valid explicit file.
- Report `input_mode=explicit_paths` for explicit accepted-event inputs.
- Fail closed for missing, invalid, parent-relative, and repository-external explicit input paths.
- Preserve no-mutation authority: no accepted state write, no Project Source mutation, no artifact adoption, no deployment, and no model execution.

Out of scope:

- Accepted-event ledger write path.
- `accept-event --write`.
- Proposal/event-intake promotion into accepted-event JSON.
- Runtime orchestration engine.
- k8s-game implementation/deployment.
- Project Source mutation changes.
- Artifact adoption/current mutation beyond later release-control adoption.

DoD target: DOD-085.

## Focused working slice — v0.1.83

```text
slice: Accepted-event ledger design scaffold
status: focused working candidate
accepted/current baseline remains: chatgpt_claudecode_workflow-2_v0.1.79.zip
working context: v0.1.82 focused-validated candidate
```

Scope:

- Add `pb orchestration ledger-status --json`.
- Define the future append-only accepted-event ledger path.
- Define the accepted-event ledger record schema path.
- Report future write preconditions and no-mutation authority.

Out of scope:

- `accept-event --write`.
- Ledger creation or append.
- Project Source mutation.
- Artifact adoption/current mutation.
- Deployment or model execution.

## Focused working slice — v0.1.84

```text
slice: Accepted-event ledger validation command
status: focused working candidate
accepted/current baseline remains: chatgpt_claudecode_workflow-2_v0.1.79.zip
working context: v0.1.83 focused-validated candidate
```

Scope:

- Add `pb orchestration validate-ledger --json`.
- Validate the accepted-event ledger scaffold without creating or writing the ledger.
- Treat an absent ledger as valid during the pre-write phase when the directory and schema scaffold are present.
- Fail closed for malformed existing ledger JSONL records.
- Preserve no-mutation authority: no accepted state write, no Project Source mutation, no artifact adoption, no deployment, and no model execution.

Out of scope:

- `accept-event --write`.
- Ledger creation or append.
- Project Source mutation.
- Artifact adoption/current mutation.
- Deployment or model execution.

DoD target: DOD-087.


## v0.1.84.1 repair plan — fresh live-test Project per run

Scope: repair validation-run Project isolation only.

- Generate a fresh release-control test Project name per invocation unless `PROMPTBRANCH_RELEASE_TEST_PROJECT_NAME` is explicitly set.
- Default `ask-live`, `visual-artifact-roundtrip`, and `release-live` to run-scoped Project prefixes.
- Keep whole-project deletion frozen and continue forcing `--keep-project`.
- Preserve explicit `--conversation-url` and `--project-name` overrides.
- Do not add ledger writes or accepted-state mutation.

Expected validation: focused parser/CLI/release-control shell tests, compileall, bash syntax, Artifact Guardian, followed by operator install and a small live command when needed.


## v0.1.84.2 repair note

`v0.1.84.2` is a repair-only candidate on top of focused `v0.1.84.1`. It changes live/browser 429 modal handling so history-sensitive operations click `Got it`, wait the configured acknowledgement cooldown, and continue polling instead of failing on a short modal timeout. It does not advance ledger/write/orchestration scope and does not re-enable ChatGPT Project deletion. Accepted/current remains `v0.1.79` until later adoption/current evidence exists.


## v0.1.84.3 repair status

Uploaded `release_control.v0.1.84.2.run_all_tests.log` ended after the release-control rate-limit retry wait line, so it did not prove a second retry failure. It did prove a release-blocking first-attempt failure in `project_ensure_create_or_reuse`: after 429 modal acknowledgement and cooldown, the ChatGPT create-project submit button stayed disabled after the project name was filled. `v0.1.84.3` repairs only that browser recovery path by adding bounded create-project disabled-submit recovery: check/acknowledge rate-limit modal again, wait configured cooldown, clear/refill the project name, dispatch input/change/keyup/blur events, tab out, reacquire the submit button, and retry enablement before failing closed with structured disabled-state logs. Project deletion remains frozen; ledger/write/orchestration scope does not advance.


## v0.1.84.4 repair status

ChatGPT Project names are limited to 50 characters. `v0.1.84.4` repairs generated test Project naming only: release-control and live-test generated names are capped at 50 characters while preserving run-scoped uniqueness through a stable hash suffix when truncation is required. Explicit `PROMPTBRANCH_RELEASE_TEST_PROJECT_NAME` values longer than 50 characters now fail fast. Project deletion remains frozen; ledger/write/orchestration scope does not advance.


## v0.1.84.5 repair status

The v0.1.84.4 full all-tests/adoption gate returned `FIX` because `visual_artifact_roundtrip` failed with `artifact_candidate_not_selected`: the ChatGPT reply envelope was near-complete but invalid JSON in one attempt due raw nested quotes inside a validation string, and another attempt had a balanced JSON object followed by a truncated `END_PROMPTBRANCH_REPLY_JSON` marker fragment. `v0.1.84.5` repairs only the visual artifact reply-envelope surface: the prompt now asks for simple validation strings without arrays/raw quotes/Markdown links, and the reply parser accepts a balanced JSON object followed only by a truncated end-marker fragment while still rejecting genuinely malformed JSON. Project deletion, ledger/write/orchestration, Project Source, artifact adoption/current, deployment, and model-execution scope do not advance.

## v0.1.84.5.1 repair status

`v0.1.84.5.1` repairs live-test Project identity and visual-roundtrip timing evidence only. `ask-live`, `visual-artifact-roundtrip`, and `release-live` now create a fresh Project with `create_project()` for mutation-capable default/`--project-name` test setup and carry the returned Project URL/id forward; they do not resolve by non-unique ChatGPT Project display name. `--conversation-url` remains the exact existing-target bypass. `pb test visual-artifact-roundtrip --json` now includes `phase_timings` for input ZIP creation, Project setup, ask, reply parse, artifact download, smoke verification, cleanup when applicable, and total elapsed time. Project deletion remains frozen; ledger/write/orchestration, Project Source, artifact adoption/current, deployment, and model-execution scope do not advance.

## v0.1.84.5.2 repair status

`v0.1.84.5.2` repairs live-test 429 telemetry propagation and non-clean validation classification only. `/v1/ask` now preserves browser-service `rate_limit_telemetry`; `pb test ask-live --json` and `pb test visual-artifact-roundtrip --json` surface rate-limit telemetry; otherwise functional live-test runs that observe backend/history `429` or ChatGPT rate-limit modal telemetry now report `status=rate_limited_contaminated` and `ok=false` instead of clean `verified`. Functional artifact evidence remains visible through `functional_status`, `verification_status`, and artifact-intake details. Project deletion remains frozen; ledger/write/orchestration, Project Source, artifact adoption/current, deployment, and model-execution scope do not advance.


## v0.1.84.5.3 repair status

`v0.1.84.5.3` repairs rate-limit telemetry aggregation evidence only. `v0.1.84.5.2` remains functionally correct for downgrade behavior; this repair deduplicates repeated event-backed telemetry snapshots from visual artifact download/smoke-verification result carrying so top-level wait/event totals are reliable. It does not change Project deletion, Project creation identity, `/v1/ask` telemetry propagation, non-clean 429 classification, Project Source, artifact adoption/current, ledger/write/orchestration, deployment, or model-execution scope.


## v0.1.84.5.4 repair plan

Repair-only: change recovered 429 telemetry from a retry-triggering failure to a warning status after functional verification succeeds. Preserve fail-closed behavior for unrecovered rate-limit evidence.


## v0.1.84.5.5 repair plan entry

Repair only: suppress release-control retries for recovered 429 telemetry after functional verification succeeds. Preserve retry/fail behavior for unrecovered 429, timeout, missing sentinel, failed artifact verification, wrong project, or any other functional failure. Do not advance ledger/write/orchestration scope.

## v0.1.84.5.6 repair note

`v0.1.84.5.6` repairs release-control `--run-all-tests` live Project reuse on top of `v0.1.84.5.5`. The run-all live phase now ensures one run-scoped ChatGPT Project once after live profile preflight and passes the returned Project URL to `ask-live`, `visual-artifact-roundtrip`, and `release-live` with `--conversation-url`. This prevents every live subtest from creating a separate retained Project while preserving delete-frozen safety, 50-character Project name caps, project-create recovery, recovered 429 retry suppression, and visual artifact reply-envelope hardening. No ledger/write/orchestration, Project Source mutation, artifact adoption/current, deployment, or model-execution scope advances.

## v0.1.84.5.7 repair note

`v0.1.84.5.7` repairs the shared live Project ensure command introduced in `v0.1.84.5.6`. Release-control `--run-all-tests` now uses the supported top-level `pb project-ensure` command to create or resolve one run-scoped ChatGPT Project, extracts the returned Project URL, and passes that exact URL to `ask-live`, `visual-artifact-roundtrip`, and `release-live` with `--conversation-url`. This preserves the one-Project-per-full-test-run policy without calling the unsupported nested `pb project ensure` surface. No project deletion, ledger/write/orchestration, Project Source mutation, artifact adoption/current, deployment, or model-execution scope advances.

## v0.1.84.5.8 repair plan entry

Repair only: add bounded Promptbranch service recovery after browser-backed `ReadTimeout` evidence during `--run-all-tests`, before continuing to the next browser-backed release-control phase. Preserve original full-test failures, retry `live_profile_preflight` at most once after recovery, and keep project deletion, ledger writes, Project Source mutation, adoption/current semantics, deployment, and model execution out of scope.

## v0.1.84.5.9 repair plan position

Repair-only candidate on top of `v0.1.84.5.8`. The active repair fixes `live_project_ensure` parsing and recovered 429 handling so the shared live Project URL returned by `pb project-ensure` is exported and downstream live steps are not skipped when the Project ensure operation succeeded functionally. No normal accepted-event ledger scope advances.

## v0.1.84.5.10 repair plan entry

Repair-only continuation from `v0.1.84.5.9`: isolate/deduplicate localhost offline release-validation groups and harden ask-live completion when a sentinel is visibly present but the UI remains in a stop/running state until timeout. Preserve project-deletion freeze, shared live Project reuse, recovered-429 retry suppression, service ReadTimeout recovery, Project Source/adoption/current semantics, and ledger no-write boundaries. Full all-tests/adoption remain the next external validation step.

## v0.1.84.5.10.1 repair plan entry

Repair-only continuation from `v0.1.84.5.10`: hard-deny browser rate-limit cooldown retry for localhost/offline release-validation step names, especially `full_localhost`, and add a regression test proving the denylist is checked before the generic `waiting ... before retry` path. Preserve live-browser rate-limit retry behavior for live steps and preserve all no-mutation boundaries.

## v0.1.84.5.10.2 repair plan entry

Repair-only continuation from `v0.1.84.5.10.1`:

1. Preserve the hard browser-cooldown retry denial for `full_localhost` and explicit localhost/offline validation groups.
2. Remove `full_direct` / `direct` from the localhost/offline denylist.
3. Rank top-level command result JSON above nested helper/metadata JSON in the all-tests summary reader.
4. Add regression coverage for nested `profile_lease.metadata` not displacing an `ask_live` `verified_with_recovered_rate_limit` command result.
5. Preserve fail-closed behavior for unrecovered 429 evidence.

No normal release slice advances in this repair.

## v0.1.84.5.10.3 repair plan entry

Repair-only continuation from `v0.1.84.5.10.2`: patch all-tests summary classification so recovered `ask_live` payloads with complete functional sentinel proof are green even when the top-level payload has `ok=false` due to rate-limit contamination bookkeeping. Add small fake-command run-all regression tests proving the recovered case is green and a functional-failure case remains red. Preserve `full_localhost` cooldown denial and keep `full_direct` outside the localhost/offline denylist.

## v0.1.84.5.11 — live validation diagnostics and source-add timeout observability

Baseline: `chatgpt_claudecode_workflow-2_v0.1.84.5.10.3.zip`.

Goal: make release-control run-all failures explain themselves quickly before the operator reruns a full live gate.

Planned work:

1. Add per-step all-tests diagnostics for transport class, browser ReadTimeout, source-add timeout, rate-limit evidence, retry policy, and likely failure phase.
2. Add full transport diagnostics to `post_release_validation.*.summary.json`.
3. Add fast fixture tests that reproduce source-add ReadTimeout and localhost rate-limit retry-denial classification without browser or Project Source mutation.
4. Preserve fail-closed behavior for real source-add failures, unrecovered 429, missing sentinels, malformed artifacts, and ChatGPT Project deletion.

Exit criteria: focused diagnostics tests, version tests, project-control tests, shell syntax, Artifact Guardian, and then the operator full `--run-all-tests --strict-source-kind-matrix --adopt-after-validation` gate.

## v0.1.84.5.12 — Explicit new-task ask mode

Baseline: `chatgpt_claudecode_workflow-2_v0.1.84.5.11.zip`.

Goal: let operators intentionally start a fresh ChatGPT Project task when the remembered conversation is stale, busy, interrupted, or otherwise unsuitable, without weakening composer safety.

Planned work:

1. Add `pb ask --new-task` / `--new-conversation` parser and help support.
2. Keep default `pb ask` routed through remembered conversation state.
3. Route `--new-task` through the remembered Project home and pass no explicit conversation URL to the browser/service layer.
4. Fail closed for `--new-task --conversation-url` and missing Project-home state.
5. Preserve no-fill safety and classify busy remembered conversations as `target_conversation_busy` with recovery guidance.
6. Update remembered conversation state only after successful fresh-task binding evidence.
7. Add focused parser/backend/browser/state tests.

Exit criteria: focused new-task tests, busy-conversation classification tests, existing service/direct ask regressions, compileall, help-text grep, project-control test, Artifact Guardian, ZIP hygiene. Full release-control/adoption remains an external operator gate.

## v0.1.84.5.12.2 repair plan — deterministic scheduler/source release-validation group

Repair-only scope from `v0.1.84.5.12.1`:

1. Replace broad `browser_scheduler_source_lifecycle` pytest `-k` selector with explicit fast nodeids.
2. Preserve required release-validation group semantics and timeout boundary.
3. Add a regression test that rejects broad `cleanup` selector reintroduction.
4. Do not change `pb ask --new-task`, Project Source mutation, artifact adoption/current, live browser semantics, or ChatGPT Project deletion behavior.


## v0.1.85 — Ask state observability and new-task proof hardening

Baseline: `chatgpt_claudecode_workflow-2_v0.1.84.5.12.2.zip`.

Goal: make the accepted `pb ask --new-task` behavior easier to prove without operator confusion around schema-v1 versus schema-v2 state paths.

Planned changes:

1. Expose schema-v2 current conversation fields in `pb state`.
2. Add `pb state --proof` for read-only state proof metadata.
3. Add a canonical short live smoke script for `pb ask --new-task` using `.current.conversation_url`.
4. Add focused tests preventing stale top-level `.conversation_url` proof usage.

Out-of-scope: MkDocs integration, backend API investigation, Project Source mutation behavior, artifact adoption behavior, and Project deletion behavior.

## v0.1.86 — K8s-game orchestration plan reconciliation

Baseline: `chatgpt_claudecode_workflow-2_v0.1.85.zip`.

Goal: reconcile the Kubernetes game orchestration plan to the real accepted/current Promptbranch baseline before starting game implementation work.

Planned work:

1. Update `docs/project/` control-surface files to state that `v0.1.85` is the accepted/current baseline for this line.
2. Refresh orchestration status and plan docs so they no longer present `v0.1.79` or older candidates as the current orchestration baseline.
3. Preserve the k8s-game as a controlled test vehicle, not a standalone product.
4. Define the next implementation path as static-first and repository-local only.
5. Keep Kubernetes mutation blocked until a later explicit dry-run/deploy evidence gate exists.

Out of scope:

```text
no game implementation
no Docker image build/publish
no Kubernetes apply
no Helm release
no cluster mutation
no Project Source mutation
no artifact adoption/current behavior change
no accepted-event ledger write
```

Exit criteria: focused project-control and orchestration-doc tests, version tests, compileall, Artifact Guardian, ZIP hygiene, then operator full release-control/adoption.

## v0.1.87 — Loop target schema and dry-run planner

Baseline: `chatgpt_claudecode_workflow-2_v0.1.86.zip`.

Goal: add the first deterministic loop target schema and dry-run planner so Promptbranch can reason over bounded problem definitions before any real action is implemented.

Planned work:

1. Define a JSON target schema for loop-based problem-solving MVP targets.
2. Add `pb loop validate --target <file>` to validate target definitions without side effects.
3. Add `pb loop plan --target <file>` to emit a deterministic dry-run loop plan.
4. Add `pb loop run --target <file> --dry-run` as stubbed control-flow output only, with no real action execution.
5. Add a static game target fixture only as a future problem target, not as game implementation.
6. Preserve no-deploy, no-mutation, no Project Source mutation, no artifact adoption, and no Project deletion boundaries.

Out of scope: real implementation actions, test command execution, file mutation by the loop, Docker/Kubernetes/Helm deployment, Project Source mutation, artifact adoption/current behavior change, and ChatGPT Project deletion behavior changes.

Exit criteria: focused loop target/schema tests, CLI loop tests, project-control tests, version tests, compileall, Artifact Guardian, ZIP hygiene, then operator release-control/adoption.

## v0.1.88 — Incremental release validation evidence reuse

Baseline: `chatgpt_claudecode_workflow-2_v0.1.87.1.zip`.

Goal: reduce duplicate validation work by allowing `--run-all-tests` to reuse prior successful `--run-tests` evidence for the same artifact and validation dimensions.

Planned work:

1. Write structured validation evidence for successful direct `pb test full` runs.
2. Include artifact SHA256 and validation dimensions in the evidence.
3. Let `--run-all-tests` reuse only matching `full_direct` evidence.
4. Keep localhost, live browser, import-smoke, and artifact-guard groups executed unless separately proven later.
5. Report `validation_reuse.reused_groups`, `executed_groups`, `invalidated_groups`, and `failed_groups` in the all-tests summary.

Out of scope: live/browser reuse, localhost reuse, adoption behavior changes, Project Source behavior changes, deployment/Kubernetes behavior, and loop-engine behavior changes.

### v0.1.88.1 repair note

Repair-only continuation of `v0.1.88`. Fix the release-blocking `project_source_add_text` timeout path by applying the extended source-mutation timeout to Docker-service source-add calls and by returning structured fail-closed diagnostics if a source mutation still times out. Do not expand evidence-reuse scope, do not change adoption semantics, and do not advance to `v0.1.89` until `v0.1.88.1` adoption/current evidence exists.

## v0.1.89 — Live validation timing visibility and shortest-path click audit

Baseline: `chatgpt_claudecode_workflow-2_v0.1.88.1.zip`.

Goal: reduce wasted live-validation time and cooldown risk by making timing and browser-action/click paths visible before repeatedly running broad `--run-all-tests`.

Planned work:

1. Attach a browser action audit to live browser operation results.
2. Record click attempts, click successes/failures, fallback strategies, repeated click labels, and a cooldown-risk score.
3. Aggregate browser action audits in `pb test report` so the operator can review whether the shortest safe path to the goal was taken.
4. Add a live validation timing summary with total browser-step duration and slowest steps.
5. Keep the change observational and fail-closed: no extra clicks are authorized by the audit itself.

Out of scope: changing Project Source mutation semantics, artifact adoption/current behavior, Project deletion behavior, Kubernetes/deployment behavior, and expanding validation evidence reuse beyond the `v0.1.88` scope.

Exit criteria: focused browser action audit tests, test-report timing/action aggregation tests, version/control-surface tests, compileall, shell syntax, Artifact Guardian, ZIP hygiene, then operator release-control/adoption.


## v0.1.90 — Conversation-history/backend-api 429 pressure reduction

Baseline: `chatgpt_claudecode_workflow-2_v0.1.89.zip`.

Goal: reduce live validation cooldown pressure by preventing non-essential global conversation-history auto-requests from repeatedly hitting the rate-limit-sensitive `/backend-api/conversations` surface.

Planned work:

1. Add a configurable conversation-history request shield for global `/backend-api/conversations` GET requests.
2. Fulfill non-essential frontend auto-requests with an empty Promptbranch-marked payload instead of letting the browser repeatedly hit the rate-limit-sensitive endpoint.
3. Preserve explicit Promptbranch history fetches by allowing them through during controlled fetch scopes.
4. Preserve project-scoped project-conversation endpoint calls.
5. Add telemetry fields for shield enabled/mode, shielded request count, explicit-fetch allowed count, and shield events.
6. Expose shield counts in the test-report rate-limit summary.

Out of scope: removing rate-limit modal handling, changing Project Source mutation semantics, changing adoption/current behavior, changing Project deletion safety, Kubernetes/deployment behavior, and loop behavior.

Exit criteria: focused request-shield tests, test-report summary tests, version/control-surface tests, compileall, shell syntax, Artifact Guardian, ZIP hygiene, then operator release-control/adoption.

### v0.1.90.1 repair note

Repair-only continuation of `v0.1.90`. Fix the release-blocking `project_source_overwrite_file` stale-inflight post-commit verification path. File-source uploads/overwrites must not advance to persistence verification on stale-inflight soft quiet; they must wait for normal save-request quiet. If a post-commit recovery loop times out but the requested source is visible on the current Project Sources surface, classify it as recovered from a visible surface snapshot. If the source remains absent, classify it explicitly as `post_commit_source_absent_after_stale_inflight`. Do not advance the conversation-history shield scope, adoption behavior, loop behavior, deployment behavior, or Project deletion behavior.

## v0.1.91 — Run-all evidence reuse proof and localhost matrix cooldown audit

### Objective

Make `--run-all-tests` prove that it reuses already-passed direct `--run-tests` evidence only when the artifact hash and validation dimensions match, while still running the missing localhost/live matrix groups.

### Required behavior

- `--run-tests --strict-source-kind-matrix` writes direct `full_direct` validation evidence.
- A later `--run-all-tests --strict-source-kind-matrix` can reuse only that identical `full_direct` evidence.
- `full_localhost` still executes and is represented in `validation_reuse.executed_groups`.
- `localhost_matrix_cooldown_audit` summarizes localhost/offline rate-limit evidence and retry-policy violations.
- Missing, stale, failed, or dimension-mismatched evidence causes rerun or failure; it must not be treated as green.

### Out of scope

No live browser behavior changes, no Project Source mutation changes, no adoption/current changes, no Project deletion changes, no loop behavior changes, and no deployment/Kubernetes behavior.


### v0.1.91.1 repair note

Repair-only continuation of `v0.1.91`. Fix the `--run-all-tests` proof failure by adding a narrow one-time retry for the first ask-live plain step when ChatGPT returns a generic null-project Retry response, while keeping concrete wrong-Project failures release-blocking. Also fix all-tests summary aggregation so successful live command payloads are not displaced by nested helper/schema JSON objects in verbose logs. Do not advance evidence-reuse scope, localhost audit scope, adoption semantics, Project deletion behavior, Project Source behavior, loop behavior, or deployment behavior.

### v0.1.91.2 repair note

Repair-only candidate from accepted/current `v0.1.91.1`. Fix only run-all final summary aggregation for noisy logs containing pretty-printed live command JSON. Preserve ask-live retry recovery, evidence reuse, localhost cooldown audit, live command behavior, adoption/current semantics, Project deletion freeze, and Project Source behavior. No normal slice advances.

## v0.1.91.3 repair plan

Repair-only objective: preserve `v0.1.91.1` accepted behavior and `v0.1.91.2` run-all aggregation repair while hardening Docker service recreate/version verification for clean-system bootstrap and stale local Docker states. Do not open `v0.1.92` until the `v0.1.91` run-all proof line is green or explicitly deferred.

## v0.1.91.4 repair plan

Repair-only objective: make release-control reproducible on a clean system with no running Docker service before Project Source add.

Required changes:

1. Preserve the `v0.1.91.1` ask-live retry repair.
2. Preserve the `v0.1.91.2` run-all summary aggregation repair.
3. Preserve the `v0.1.91.3` Docker recreate/version verification hardening.
4. Reinstall the candidate CLI before service-mediated Project Source mutation.
5. Verify the pre-source-add service health/version before `promptbranch src add`.
6. If missing or stale and service management is enabled, bootstrap the candidate Docker service before source add.
7. Classify clean-system absence as `pre_source_add_service_unavailable` with diagnostics.
8. Do not change adoption/current semantics, Project deletion behavior, live/browser behavior, or Project Source mutation semantics.


## v0.1.91.5 repair plan

Repair only the final all-tests summary aggregation for `live_project_ensure` payload selection. Preserve ask-live retry, run-all pretty JSON extraction, Docker recreate hardening, pre-source-add service bootstrap, adoption semantics, and Project deletion freeze.


## v0.1.91.6 repair plan

Repair only the adopt-after-validation verifier path after a green run-all summary with reused direct evidence. Preserve all `v0.1.91.1` through `v0.1.91.5` repairs. Do not alter validation semantics, live/browser behavior, adoption/current semantics, Project Source mutation, or Project deletion behavior.


## v0.1.91.7 repair plan

Repair only the pre-source-add Docker bootstrap freshness failure where a cached `COPY . .` layer can contain stale version surfaces. Preserve all `v0.1.91.1` through `v0.1.91.6` repairs. Required behavior: use explicit `--project-directory "$repo_root"`, absolute compose file path, `build --no-cache --pull`, repo version-surface diagnostics before build, and fail-closed classification for `pre_source_add_docker_build_context_version_mismatch`.


## v0.1.91.8 repair plan

Repair only the duplicate live browser/source lifecycle in the localhost leg of `--run-all-tests`. Preserve all `v0.1.91.1` through `v0.1.91.7` repairs. Required behavior: run the live browser/source lifecycle once through direct validation, reuse matching direct evidence for `full_localhost`, keep localhost service/report/cooldown audit visibility, and fail closed when evidence dimensions do not match.

## v0.1.91.9 repair plan

Repair the final `v0.1.91.8` adoption-footer path assumption by allowing a green all-tests summary plus validated direct evidence and a `full_localhost` `reused_browser_source_lifecycle` step to satisfy adoption verification when the localhost report file is absent by design. Add incremental run-all progress output so long validation runs expose tested/succeeded/failed percentages before completion.
