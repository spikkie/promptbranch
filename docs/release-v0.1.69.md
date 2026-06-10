# Release v0.1.69

## Slice

Browser-profile busy retry and source-add idle barrier.

## Baseline

```text
chatgpt_claudecode_workflow-2_v0.1.68.zip
```

v0.1.68 is the accepted/current baseline based on operator-provided `pb artifact current --json` evidence and a verified full-test report.

## Problem

A live my_awx 0.0.199 release lifecycle reached accepted validation but failed adoption when a follow-up Project Sources read hit:

```text
status: browser_profile_busy
active_operation: add_project_source
operator_action: retry_after_active_browser_operation_or_use_async_job_status
```

The source-add operation had returned, but the shared service browser profile had not yet reached an observable idle state.

## Changes

- Added `pb browser wait-idle --json` with timeout and poll controls.
- Added an automatic post-mutation browser-idle barrier after successful `pb src add` / `project-source-add` unless explicitly disabled.
- Added structured `browser_profile_busy` retry guidance for `pb src list`.
- Added structured `browser_profile_busy` handling when artifact adoption cannot verify Project Sources because the browser profile is still active.
- Added focused parser and CLI tests for wait-idle, post-source-add wait, and source-list busy guidance.
- Updated `docs/project/` to treat v0.1.68 as the accepted/current baseline and v0.1.69 as the candidate.

## Out of scope

- No broad browser automation rewrite.
- No deployment behavior changes.
- No autonomous repository editing.
- No broad native release lifecycle replacement.

## Validation

```text
python3 -m pytest -q   tests/test_cli_parser.py::test_parser_accepts_browser_status_and_source_add_profile_wait   tests/test_promptbranch_cli.py::test_browser_wait_idle_polls_until_available   tests/test_promptbranch_cli.py::test_src_add_waits_for_browser_idle_after_success   tests/test_promptbranch_cli.py::test_src_list_browser_profile_busy_reports_wait_idle_guidance   tests/test_promptbranch_cli.py::test_src_add_promotes_browser_profile_busy_to_top_level_payload   tests/test_promptbranch_cli.py::test_browser_status_command_uses_service_client

python3 -m pytest -q tests/test_project_control_surface.py
python3 -m compileall -q .
ZIP hygiene check
```

Full tests were not run by the assistant for this candidate.

## Adoption status

```text
candidate only
```

Do not call this release accepted/current until adoption evidence confirms runtime, state artifact, state source, registry current, and consistency alignment.
