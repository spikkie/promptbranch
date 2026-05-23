# Release v0.0.264

## Summary

Adds a first-class read-only release-readiness gate command on top of the built-in `release-readiness` skill introduced in v0.0.263.

## Changes

- Added `pb agent release-readiness --json`.
- Added `pb agent release-readiness --require-ready --json` for CI/finalizer-friendly precondition checks.
- Added deterministic gate output with `passed`, `blockers`, `warnings`, and `report_status`.
- Preserved read-only MCP stdio execution and blocked write/source/artifact mutation.
- Added parser and unit coverage for the new command and gate behavior.

## Non-goals

- No source sync automation.
- No artifact release/adoption automation.
- No Project Source mutation.
- No Git commit or push.

## Validation

Validated with compile, focused parser/MCP tests, extracted ZIP smoke, and ZIP hygiene checks.
