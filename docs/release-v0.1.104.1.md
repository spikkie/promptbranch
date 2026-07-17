# Release v0.1.104.1

Repair candidate for mandatory sandbox rollback release evidence.

## Added

- Required `sandbox_mutation_rollback_gate` release-validation group.
- Explicit tenth `--run-all-tests` sandbox gate.
- Exact 13-gate structured verifier.
- Release-validation manifest SHA-256 in the full-test evidence signature.
- Fresh-direct policy for this repair candidate.

## Preserved

- Accepted/current remains `v0.1.103.10.116` until adoption.
- `full_localhost` executes independently.
- Sandbox-only mutation, exact validation, rollback, repository immutability and cleanup behavior from `v0.1.104`.
- All browser, profile, Project Source overwrite, adoption and assigned-source verification behavior from the accepted repair line.
