# Release v0.0.246 — Read-only release doctor artifact hardening

Base release: v0.0.245.13
Release version: v0.0.246
Release type: normal

## Scope

This release adds read-only `pb release doctor --artifact ZIP` hardening.
It does not install, upload, migrate, adopt, commit, push, or mutate project state.

## Changes

- Added `--artifact` to `pb release doctor`.
- Added read-only candidate ZIP inspection:
  - path presence
  - filename version
  - `VERSION` file version inside ZIP
  - SHA256
  - size and entry count
  - wrapper-folder detection
  - ZIP hygiene and nested-ZIP counts
- Added artifact/runtime/source consistency checks:
  - artifact ZIP version vs runtime code version
  - artifact ZIP version vs working-tree `VERSION`
  - artifact ZIP visibility in Project Sources when source listing is enabled
  - artifact ZIP version vs adopted source/artifact/registry state
- Added `lifecycle_phase` classification:
  - `runtime_only`
  - `candidate_zip_available`
  - `project_source_uploaded`
  - `adopted_current`
  - `lifecycle_ready`
  - `lifecycle_blocked`
- Added parser and regression coverage for the new read-only artifact doctor path.

## Validation performed

- `python3 -m py_compile promptbranch_cli.py`
- focused release-doctor parser and artifact hardening tests
- focused container/API/MCP/CLI parser test groups

## Safety confirmation

No slice or lifecycle mutation was performed by this release. `pb release doctor --artifact` remains read-only.
