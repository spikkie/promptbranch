# Release v0.1.125.3

## Classification

Repair release. Accepted/current remains `v0.1.124` until the exact `v0.1.125.3` candidate completes testing, explicit acceptance, adoption, and final convergence verification.

## Problem repaired

`v0.1.125.2` passed the direct full release test 52/52, but the following canonical candidate test returned `candidate_not_found` because candidate registration remained a separate operator-managed step:

```bash
pb artifact candidate-test --version v0.1.125.2 --profile full --test-timeout 3600 --json
```

The failure demonstrated that Promptbranch had several individually valid release commands but no single authoritative release state machine.

## Changes

`v0.1.125.3` introduces:

- one schema `promptbranch.release_attempt` version `2.0` durable attempt;
- immutable repository/version/SHA artifact binding;
- sequential guarded states from `DECLARED` through `FINAL_VERIFIED`;
- automatic candidate registration after artifact verification;
- independent verification for every reached state;
- clean-extraction, exact-byte, hermetic candidate testing;
- SHA-bound candidate-test evidence;
- explicit acceptance and adoption guards;
- derived candidate projection recovery;
- deterministic interruption resume and completed-run idempotency;
- positive-only Git, push, Project Source, and adoption authorization;
- a mandatory release-state-machine validation group and dedicated test suite.

The `v0.1.125.1` isolated-compileall repair and `v0.1.125.2` version-independent authority-drift repair are retained.

## Canonical command

```bash
pb release run \
  --artifact chatgpt_claudecode_workflow-2_v0.1.125.3.zip \
  --version v0.1.125.3 \
  --baseline-version v0.1.124 \
  --release-type repair \
  --profile full \
  --test-timeout 3600 \
  --until final-verified \
  --adopt \
  --json
```

No Git or Project Source mutation occurs unless explicitly requested.

## Verification

```bash
pb release verify \
  --version v0.1.125.3 \
  --repo-path . \
  --all-states \
  --json
```

Required successful terminal evidence:

```text
current_state=FINAL_VERIFIED
all_states_verified=true
failed_invariants=[]
next_transition=null
lifecycle_complete=true
```

## Scope boundary

This repair changes release orchestration and verification only. It does not advance the normal `v0.1.125` feature scope, begin `v0.1.126`, authorize external-application work, or claim acceptance before live lifecycle proof.
