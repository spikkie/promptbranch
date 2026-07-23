# Promptbranch v0.1.108.1

## Title

Project Source staged-overwrite and removal-proof reliability.

## Baseline

Accepted/current remains `v0.1.107`. This is a repair of the unadopted `v0.1.108` candidate.

## Changes

- Captures structured failed-request diagnostics for staged uploads.
- Separates file-input submission, backend request start, commit, processing stream, assigned filename, and backing identity evidence.
- Adds exactly one fail-closed retry when no mutation identity exists and the original source remains verified.
- Preserves the old source until replacement identity is complete.
- Replaces boolean disappearance inference with `verified_absent`, `still_present`, and `surface_unresolved` authority results.
- Requires two stable refreshed observations for removal success.
- Adds deterministic regression coverage.
- Adds `pb test project-source-file-reliability` as a narrow development preflight with independent overwrite and removal scenarios.

## Validation completed in the candidate build

- Relevant source/service/integration/test-suite tests: 268 passed.
- Focused CLI parser and dispatch tests: passed.
- Full focused direct and localhost live profiles: pending operator runtime validation.
- Full release-control validation and adoption: not run in the candidate build environment.

## Promotion contract

The focused live profile is not adoption-grade evidence. Both focused transports should pass before running release control, and adoption still requires all gates including independently green `full_direct` and `full_localhost`.

## Scope boundary

`v0.1.109 — PROJECT_SETTINGS.md, AGENTS.md and project authority-graph definition` remains planned_after_acceptance and is not implemented here.
