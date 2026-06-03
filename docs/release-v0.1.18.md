# Release v0.1.18

## Scope

Read-only full-test/adoption checkpoint preparation once the focused-development threshold is reached.

## Changes

- Extended `pb release status-guide --json` so threshold-reached development candidates expose an actionable runbook.
- Added explicit full release-control and adopt-current-after-green-full-test command recommendations.
- Preserved read-only behavior for status-guide itself; it does not run tests, adopt, upload sources, or mutate Git.
- Updated the living design Markdown and `.drawio` source to reflect the v0.1.18 checkpoint-prep behavior.

## Validation

Focused validation was performed during artifact creation. Full browser/service/adoption validation is intentionally deferred to the operator checkpoint after installing this candidate.
