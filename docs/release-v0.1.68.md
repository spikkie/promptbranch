# Release v0.1.68

## Slice

Project Sources add performance and transactional diagnostics.

## Baseline

```text
Build input: chatgpt_claudecode_workflow-2_v0.1.67.zip
Adoption-evidenced baseline in docs/project: chatgpt_claudecode_workflow-2_v0.1.66.zip
```

v0.1.68 is a candidate release. It must not be called accepted/current until adoption evidence confirms alignment.

## Changes

- Added an add-new-source fast path for file source add when the initial Project Sources snapshot is empty.
- Reduced non-empty absence preflight from the previous multi-step wait/refresh path to a short bounded probe.
- Added structured failure results for overwrite upload/persistence failures after an existing source was removed.
- Added persistence false-negative diagnostics with save-request summary and recovery guidance.
- Added focused tests for fast path, reduced absence preflight, overwrite failure recovery, and persistence false-negative diagnostics.

## Validation

```text
Targeted tests: tests/test_project_source_capabilities.py selection
Control surface: tests/test_project_control_surface.py
Compile: python3 -m compileall -q .
ZIP hygiene: pending final package check
Full tests: not run in this environment
```

## Out of scope

- Backend-first Project Sources API replacement.
- Source sync rewrite.
- Release lifecycle adoption.
- Deployment or runtime service behavior changes outside source-add handling.
