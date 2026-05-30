# Release v0.0.278.68

## Scope

Add a clear `ask-live` test profile for the visible/local operator workflow.

This release builds on `v0.0.278.67`, which is accepted for direct/localhost service-transport testing. It does not change the repaired `pb ask` fill/submit behavior.

## Changes

- Add `pb test ask-live --json`.
- Make `ask-live` default to local headed/debug browser mode.
- Default `ask-live` to `./.pb_profile_local_debug` when `--profile-dir` is not supplied.
- Keep the profile separate from `localhost` service transport.
- Cover the operator ask workflow with these default steps:
  - `plain`
  - `repeated_stale_first`
  - `repeated_stale_second`
  - `prompt_file`
  - `file_attachment`
  - `prompt_file_with_attachment`
- Add `--only` and `--skip` selectors for narrowing live runs.
- Add structured JSON output with per-step sentinel validation and submit evidence when available.

## Example

```bash
pb test ask-live --json \
  --profile-dir ./.pb_profile_local_debug \
  2>&1 | tee pb_test.ask_live.v0.0.278.68.log
```

Narrow smoke:

```bash
pb test ask-live --json --only plain,prompt_file
```

## Non-goals

- No release-control integration for `--run-ask-live-tests` yet.
- No artifact download live profile yet.
- No change to `--test-transport direct|localhost|both`.
- No change to answer-text normalization.

## Validation

Focused validation for this release should include parser dispatch, ask-live command dispatch using a fake backend, shell syntax, and compile checks.
