# Repair v0.1.126.1.1.1.1.2 — Accepted-runtime precondition and preservation

## Baseline authority

- Repair input candidate: `chatgpt_claudecode_workflow-2_v0.1.126.1.1.1.1.1.zip`
- Repair input SHA-256: `264507a4921e1f885717ca0498581a352cf5e54a1b6c57363daba98522a0eb11`
- Accepted/current release remains: `v0.1.125.3.4.2`
- Accepted/current artifact SHA-256 remains: `ed6752cc7e1cf654f0e3ea505110599d5be3e067dbb00f07b8ae90cf34a9510f`
- Scope advancement: forbidden; this is a repair of the active `v0.1.126` proof chain.

## Observed defect

The live `v0.1.126.1.1.1.1.1` attempt reached `RUNTIME_PREPARED` while the accepted/current production runtime on port `8000` was already unavailable. Its persisted evidence recorded both `accepted_runtime_before.present=false` and `accepted_runtime_after.present=false`, yet `accepted_runtime_unchanged=true` and the transition succeeded.

That violated the production-preservation invariant. "Absent before and absent after" is not a valid preservation proof.

## Repair

`RUNTIME_PREPARED` now fails closed unless the accepted/current runtime is proven before candidate runtime mutation as:

- Docker inventory readable;
- exactly one authoritative container bound to port `8000`;
- container present;
- health `ok=true`;
- health version exactly equals the configured accepted baseline version;
- authoritative Docker image inspect succeeds;
- image version label exactly equals the accepted baseline version;
- image artifact SHA label is present.

The precondition is refreshed on every retry. An operator can therefore restore the accepted service and rerun the same attempt without deleting the runtime checkpoint.

After isolated candidate preparation, Promptbranch re-probes production and requires:

- the same exact accepted-runtime preconditions still pass;
- authoritative container identity is unchanged;
- immutable Docker image ID is unchanged;
- accepted artifact SHA label is unchanged.

Any missing, unhealthy, mismatched, disappeared, or drifted accepted runtime blocks the release before `TESTED_GREEN`.

## Recovery policy

This repair does not auto-start, auto-recreate, or auto-promote production from candidate preparation. Production recovery remains an explicit operator action. Candidate validation may observe production but may not silently repair it.

## Validation target

Focused deterministic proof must cover:

1. accepted runtime absent before preparation → blocked retryable before candidate install/build/start;
2. accepted runtime unhealthy → blocked retryable;
3. accepted runtime baseline-version mismatch → blocked retryable;
4. accepted runtime disappears during candidate preparation → blocked retryable;
5. accepted Docker image/artifact identity drifts → blocked retryable;
6. operator restores production and retries → accepted runtime is re-snapshotted and the isolated candidate path can continue;
7. healthy exact accepted runtime remains unchanged → `RUNTIME_PREPARED` succeeds;
8. release-state verifier independently rejects stale runtime evidence that lacks the stronger accepted-runtime proof.

Full live lifecycle validation through `FINAL_VERIFIED` remains pending after construction.
