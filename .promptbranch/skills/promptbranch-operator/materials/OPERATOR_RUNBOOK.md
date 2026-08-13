# Promptbranch operator runbook

1. Resolve repo/project/task/artifact identities.
2. Inspect current state and git state.
3. Classify risk and required authority.
4. State preconditions, expected evidence and failure codes.
5. Use the current canonical PB command/control path.
6. Verify the transition independently.
7. Record exact version/SHA/conversation identities where applicable.
8. Stop on ambiguity or collateral mutation.

For releases, preserve one artifact SHA through validation, candidate runtime, acceptance, adoption/current and final verification.

## External repository skill sync

Use `pb skill sync --target <repo>` rather than manually copying portable skill ZIP contents. Sync must resolve the source PB repository's tracked Project identity, bind to authoritative `adopted/current`, export and verify deterministic bundles from that exact artifact, stage the target mutation, atomically replace managed skill directories with rollback on failure, write pinned provenance, validate the target skills, and report Git changes. It never commits or pushes the target repository.

Local modifications to previously managed skill trees fail closed unless the operator explicitly supplies `--force`. Unmanaged same-name skill directories also fail closed unless forced. `--dry-run` performs authority resolution and bundle proof without target mutation.
