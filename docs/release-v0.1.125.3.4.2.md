# Release v0.1.125.3.4.2

## Purpose

Repair the final canonical v0.1.125 lifecycle contradiction exposed by the adopted/current `v0.1.125.3.4.1` runtime.

`v0.1.125.3.4.1` passed the full candidate suite 53/53, was accepted and adopted, promoted the exact tested Docker image to the authoritative service on port 8000, verified version/SHA/release-attempt identity, and cleaned the isolated candidate runtimes. `FINAL_VERIFIED` nevertheless failed because the verifier re-probed the intentionally retired candidate endpoint.

## Clean replacement semantics

This release does not preserve the obsolete verifier behavior as a compatibility path.

- Before `ADOPTED_CURRENT`, `RUNTIME_PREPARED` requires the isolated candidate endpoint to be live and exact.
- At or after `ADOPTED_CURRENT`, the candidate endpoint is expected to be retired. Historical verification instead requires immutable checkpoint evidence proving candidate health and image/container identity at preparation time.
- Post-adoption verification requires successful candidate cleanup and evidence that the production Docker image id is exactly the tested candidate image id.
- The authoritative port-8000 service remains a live invariant through `ADOPTED_CURRENT` and `FINAL_VERIFIED`.
- The acceptance compatibility fallback is removed. A successful acceptance command that does not produce the canonical accepted-candidate projection fails closed.

## Baseline and target

- baseline: `v0.1.125.3.4.1`
- target: `v0.1.125.3.4.2`
- release type: repair
- next normal release after acceptance: `v0.1.126 — Persistent whole-release ETA estimator`

## Acceptance proof

The release is complete only when the canonical lifecycle reaches:

```text
current_state=FINAL_VERIFIED
failure_state=null
all_reached_states_verified=true
failed_invariants=[]
next_transition=null
lifecycle_complete=true
```

The production service on port 8000 must report `0.1.125.3.4.2` and exact artifact/release-attempt labels, while isolated candidate containers are absent.
