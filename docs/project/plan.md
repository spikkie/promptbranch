# Project Plan

## Current baseline

```text
accepted/current baseline with adoption evidence: chatgpt_claudecode_workflow-2_v0.1.68.zip
accepted checksum: fd55f38e290d77b2fcae637721ecf2ca25a7d16ceb66954f1a5497cacc30ed6d
next normal target: chatgpt_claudecode_workflow-2_v0.1.69.zip
release line: v0.1.x JSON orchestration / Promptbranch workflow control-plane hardening
```

## Plan summary

```text
Keep release slices narrow. v0.1.69 hardens browser-backed Project Source and adoption sequencing after the observed my_awx 0.0.199 lifecycle race: source add completed, but a following source-list/adoption verification hit browser_profile_busy because the shared service profile had not reached an observable idle state yet.
```

## Release / slice plan

| Version | Slice | Goal | Scope | Out of scope | Expected validation | Status |
|---|---|---|---|---|---|---|
| v0.1.66 | Release doctor config-aware candidate ZIP precheck | Make release doctor consume `.promptbranch-release.yml` for read-only candidate ZIP inspection | release doctor/config docs and tests | install, upload Project Sources, adoption, state update, commit, push | focused release config/doctor/docs-status tests | accepted_current |
| v0.1.67 | Project MVP / DoD / Plan control surface migration | Create `docs/project/` and focused validator while preserving old docs | `docs/project/*`, `tests/test_project_control_surface.py`, release metadata | runtime behavior, deployment behavior, source mutation, artifact adoption, old-doc deletion | focused control-surface validator | superseded by later accepted baseline |
| v0.1.68 | Project Sources add performance and transactional diagnostics | Reduce new-source add latency and return safer diagnostics after overwrite/persistence failures | source-add preflight/verification path, focused source-add tests, project status docs | broad lifecycle rewrite, deployment behavior | full v0.1.68 test report supplied by operator | accepted_current |
| v0.1.69 | Browser-profile busy retry and source-add idle barrier | Prevent lifecycle adoption/source-list verification from racing a just-finished Project Source browser mutation | `pb browser wait-idle`, post-source-add idle barrier, structured busy payloads for `src list`/artifact adoption verification, focused tests, status docs | runtime ask behavior, deployment behavior, autonomous execution, broad release lifecycle migration | focused browser/source/adoption parser tests, project control-surface test, compileall, ZIP hygiene | candidate |

## Slice definition — v0.1.69

```text
Release: v0.1.69
Baseline: chatgpt_claudecode_workflow-2_v0.1.68.zip accepted/current with operator full-test evidence.
Type: normal candidate
Slice: Browser-profile busy retry and source-add idle barrier
Goal: make source add, source list, and artifact adoption verification safer when a service-backed browser profile is still active after a Project Source mutation.
In scope: `pb browser wait-idle`, automatic post-source-add idle barrier, structured `browser_profile_busy` guidance for `pb src list`, structured busy handling for artifact adoption source-list verification, focused tests, version metadata, docs/project status updates.
Out of scope: browser automation rewrite, source API replacement, deployment behavior, autonomous repo editing, broad native release lifecycle ownership.
Expected files: `promptbranch_cli.py`, `tests/test_promptbranch_cli.py`, `tests/test_cli_parser.py`, version files, `docs/project/*`, `docs/release-v0.1.69.md`.
Expected validation: targeted parser/browser/source tests, project control-surface pytest, Python compileall, ZIP hygiene.
DoD movement: add DOD-013 for browser-idle barrier/source-adoption contention handling; move done after focused tests pass; DOD-009 moves to done after ZIP hygiene.
Risk: post-mutation idle polling must not falsely treat a stale lock file as active when `browser status` reports available.
Next step: install/test v0.1.69 candidate; do not mark accepted/current until `pb artifact current --json` confirms alignment.
```
