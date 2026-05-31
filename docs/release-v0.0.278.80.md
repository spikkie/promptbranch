# Release v0.0.278.80

Narrow visual-artifact-roundtrip project-isolation repair.

## Base artifact

```text
chatgpt_claudecode_workflow_v0.0.278.79.zip
```

## Target artifact

```text
chatgpt_claudecode_workflow_v0.0.278.80.zip
```

## Problem

`pb test visual-artifact-roundtrip` could run from a plain ChatGPT conversation instead of a project-scoped conversation.  When ChatGPT generated the output ZIP, browser-assisted artifact retrieval could then fail because the conversation URL was not anchored inside a removable ChatGPT Project.

## Changes

- `pb test visual-artifact-roundtrip` now creates an isolated temporary ChatGPT Project by default.
- The generated visual ZIP ask is sent with the temporary project URL as the conversation target.
- The response conversation is checked against the expected project id, accepting ChatGPT slugged project URLs.
- The temporary project is removed after download/verification unless `--keep-project` is used.
- `--conversation-url` can be used to explicitly run against an existing project conversation or project URL.
- Added parser flags for `--keep-project`, `--conversation-url`, project name/prefix/icon/color, and memory mode.
- Added structured result fields for project creation, project cleanup, project id comparison, and whether a temporary project was used.

## Safety

No artifact-intake validation was relaxed.  The visual roundtrip still requires a valid Promptbranch reply envelope, a real downloadable ZIP candidate, ZIP smoke verification, and no release/adoption state mutation.

## Validation

Focused validation performed:

```text
python3 -m compileall -q .
pytest -q tests/test_promptbranch_cli.py::test_visual_artifact_roundtrip_prompt_requires_full_reply_schema \
          tests/test_promptbranch_cli.py::test_visual_artifact_roundtrip_wraps_ask_and_artifact_intake \
          tests/test_promptbranch_cli.py::test_visual_artifact_roundtrip_explicit_conversation_url_skips_temp_project \
          tests/test_cli_parser.py::test_parser_accepts_canonical_test_profile_shortcuts
```

## Operator command

```bash
pb test visual-artifact-roundtrip --json \
  --profile-dir ./.pb_profile_local_debug \
  --keep-open
```

## Expected interpretation

If v0.0.278.80 succeeds, the earlier artifact-download failure was caused by running the generated ZIP answer outside a project-scoped conversation.  If it still fails, inspect the new `conversation_url`, `response_project_home_url`, `in_expected_project`, and download/verification fields before changing artifact intake.
