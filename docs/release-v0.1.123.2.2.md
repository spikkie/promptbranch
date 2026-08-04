# v0.1.123.2.2 — Release-control post-join Project alias verification repair

`v0.1.123.2.2` is a repair-only release from the non-adopted `v0.1.123.2.1` candidate bytes, while accepted/current remains `v0.1.123.1`.

## Defect

`pb project join` correctly reconciled a bare requested Project identity with the tracked slugged identity, but the release-control caller then compared the returned tracked values to the requested values literally and raised `joined identity mismatch` before strict validation.

## Repair

- Canonicalize both the tracked identity and `pb project join` result through the immutable `g-p-<32-hex>` Project UUID.
- Accept bare/slugged aliases only when both immutable UUIDs match.
- Keep `repo_id` exact.
- Preserve the tracked `.promptbranch-repo.json` bytes.
- Reject true cross-project UUID mismatches.
- Cover the exact embedded release-control post-join verifier, including alias success, mismatch rejection, and binding immutability.

## Scope

Repair-only. Formal MVP proof remains `0/2`; `v0.1.124` and `v0.1.125` remain normal proof cycles 1 and 2.
