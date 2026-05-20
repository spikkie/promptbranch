# Release v0.0.245

Scope: read-only release lifecycle reconciliation doctor.

## Changes

- Adds `pb release doctor --json`.
- Aggregates runtime version, VERSION file, installed distribution metadata, service `/healthz`, artifact current state, Project Sources visible versions, candidate precondition/next state, and Git cleanliness.
- Emits warning/blocker codes plus `next_safe_actions`.
- Remains read-only: no artifact download, migration, candidate-test, adoption, Project Source mutation, registry update, state update, commit, or push.

## Validation

- Focused CLI parser and release-doctor tests.
- Python compile check.
- ZIP root/hygiene verification.
