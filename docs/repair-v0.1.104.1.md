# Repair v0.1.104.1 — sandbox release-gate integration and fresh validation evidence

## Baseline

- Accepted/current: `v0.1.103.10.116`
- Failed candidate repaired: `v0.1.104`
- `v0.1.104` implemented the sandbox mutation/validation/rollback mechanism but strict host validation failed and adoption was refused.

## Problem

The sandbox proof was covered by focused tests but was not an explicit mandatory all-tests result. The strict run also reused previous `full_direct` evidence, so the final candidate implementation was not freshly exercised in that transport.

## Repair contract

1. Preserve the `v0.1.104` sandbox implementation and authority boundaries.
2. Add `sandbox_mutation_rollback_gate` to `RELEASE_VALIDATION_GROUPS` as required.
3. Execute an explicit top-level all-tests step with the same verifier.
4. Require exact terminal status `sandbox_mutation_verified_and_rolled_back`.
5. Require all 13 named gates, exact before/after evidence, validation immutability, repository immutability, rollback equality and workspace deletion.
6. Hash the complete release-validation manifest into reusable evidence identity.
7. Forbid `full_direct` evidence reuse for `v0.1.104.1`.
8. Preserve independent `full_localhost` execution.
9. Do not change browser/live behavior based on the single `target_conversation_busy` occurrence.
10. Do not adopt unless the complete strict release workflow reaches `GO`.

## Out of scope

- repository mutation from the loop;
- deployment or Kubernetes mutation;
- Project Source mutation or artifact adoption from the loop;
- browser workaround changes;
- ChatGPT Project deletion;
- promotion-readiness scope from `v0.1.105`.
