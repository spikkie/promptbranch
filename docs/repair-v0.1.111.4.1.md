# Repair v0.1.111.4.1 — Capacity-aware Project Source family replacement verification

## Baseline

- Accepted/current remains `v0.1.109.1.1`.
- `v0.1.111.4` remains unadopted and repair-required.
- The external-live idle-handoff implementation from `v0.1.111.4` is retained unchanged.

## Reproduced blocker

At Project Source capacity 25, release control successfully:

1. removed one obsolete release source (`25 → 24`),
2. uploaded the new indexed candidate (`24 → 25`), and
3. removed the previous same-family candidate (`25 → 24`).

The final verifier then incorrectly required the authoritative final count to equal the hard limit (`24 == 25`) and returned `source_capacity_final_count_not_verified` before any release tests ran.

## Corrective contract

The expected final count is calculated from proven deltas:

```text
expected_final = capacity_before - pruned_count + uploaded_count - previous_family_removed_count
```

For the reproduced transaction:

```text
25 - 1 + 1 - 1 = 24
```

Success additionally requires:

- authoritative final count equals the calculated count and does not exceed the limit;
- exact final source identity multiset equals the expected transaction result;
- exactly one assigned candidate family member remains;
- no previous family member remains;
- the pruned source remains absent;
- no unexpected source disappears or appears.

Any mismatch remains release-blocking and operator-review-required.

## Scope exclusions

- no ETA implementation;
- no PBAI-001 work;
- no weakening of Project Source mutation proof;
- no change to accepted/current authority;
- no automatic adoption.
