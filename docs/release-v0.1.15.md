# Release v0.1.15

## Scope

Read-only `pb release status-guide` operator-runbook hardening.

## Changes

- Extended `pb release status-guide --json` with `recommended_sequence`, a context-sensitive ordered list of read-only commands.
- Added `operator_runbook.required_step_count` so scripts and humans can see which commands are required for the detected release context.
- Development-candidate guidance now recommends both `pb release checkpoint --mode continue --json` and `pb test smoke --json`.
- Post-adoption guidance continues to point to `pb release baseline-status --json` as the accepted-baseline verifier.
- Plain-text `status-guide` output now prints the required step count and recommended steps.
- Updated living design Markdown and draw.io source to document the runbook role.

## Validation

Focused validation was run for release-status guidance, parser coverage, checkpoint/dev-status/baseline-status related tests, docs-status, compileall, orchestration examples, release plans, import-plan, and ZIP hygiene.

## Boundary

This release is read-only. It does not install, upload Project Sources, run full tests, adopt, update artifact state, commit, or push.
