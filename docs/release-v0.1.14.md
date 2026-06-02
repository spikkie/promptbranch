# Release v0.1.14

## Scope

Read-only release-status command guidance.

## Changes

- Added `pb release status-guide --json`.
- The command chooses the correct read-only status surface for the current lifecycle context:
  - `baseline-status` after adoption,
  - `checkpoint` for installed-but-not-adopted development candidates,
  - `dev-status` for inventory and development-head inspection.
- Added JSON and plain-text output for the command guide.
- Updated the living MVP design Markdown and draw.io source to document the command-selection role.

## Validation

Focused validation was run for parser coverage, release-status guidance, baseline-status, checkpoint, dev-status, docs-status, compileall, orchestration examples, release plans, import-plan, and ZIP hygiene.

## Boundary

This release is read-only. It does not install, upload Project Sources, run full tests, adopt, update artifact state, commit, or push.
