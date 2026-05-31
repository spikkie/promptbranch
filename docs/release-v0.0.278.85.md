# Release v0.0.278.85

## Scope

Add a deterministic, non-visual artifact roundtrip test profile and include it in the default full-suite path through the agent profile.

## Changes

- Added `pb test artifact-roundtrip --json`.
- Added host-side synthetic reply-envelope parsing, artifact candidate selection, local ZIP materialization, and exact content verification.
- Added fail-closed regression checks for malformed reply JSON, wrong filename, wrong ZIP content, and wrapper-folder ZIP layout.
- Included the deterministic artifact roundtrip in the agent profile, so `pb test full --json` covers it without requiring ChatGPT UI, browser auth, network, or rate-limit-sensitive model behavior.

## Boundary

This release does not change `pb test visual-artifact-roundtrip`. The visual/live browser roundtrip remains a separate live gate.
