# Release v0.0.270

## Base

`chatgpt_claudecode_workflow_v0.0.269.1.zip`

## Scope

Human-readable lifecycle-status and finalizer summary output only.

## Changes

- Added a human-readable renderer for `pb release lifecycle-status` when `--json` is not used.
- Added a concise terminal summary to `scripts/post-release-validation.sh` after the structured summary JSON is written.
- Preserved the existing machine-readable lifecycle-status and post-release JSON contracts.

## Explicit non-goals

- No artifact intake semantic changes.
- No install, upload, adopt, policy-sync, Git commit, or Git push behavior changes.
- No new service or Project Source probes.

## Validation

Focused parser, lifecycle-status, MCP/version, and post-release finalizer summary rendering tests were run before packaging.
