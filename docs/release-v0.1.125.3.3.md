# Release v0.1.125.3.3

## Classification

Repair release derived from the exact accepted/current `v0.1.125.3.2` artifact. The repair is limited to acceptance/adoption transactional reconciliation in the canonical release state machine.

## Live defect repaired

The `v0.1.125.3.2` candidate passed the exact SHA-bound full candidate test and its low-level `artifact accept-candidate --adopt-if-green` subprocess returned exit code `0`. The acceptance command mutated the authoritative candidate/current projections successfully, but the state-machine wrapper selected a nested consistency object instead of the complete top-level acceptance result. The durable release attempt therefore remained at `TESTED_GREEN` while the candidate registry and current artifact state already reported `v0.1.125.3.2` accepted/current.

## Action-aware command result authority

Acceptance and current-state subprocess output is parsed as complete top-level JSON documents. The only eligible acceptance result has:

```text
action=artifact_accept_candidate
```

The only eligible current-state results have:

```text
action=artifact_current
action=artifact_current_all
```

Nested dictionaries are never independent command results. Missing, ambiguous, or structurally invalid results fail closed.

## Post-side-effect reconciliation

After any failed, timed-out, missing, ambiguous, or invalid acceptance result, the state machine immediately re-reads:

- the exact candidate projection selected by repo/version/SHA;
- accepted/adoption flags;
- the current repository artifact/source projection;
- current-registry filename, version, and SHA-256.

When those authorities already prove the exact candidate accepted/current, the transition records `accepted_candidate_reconciled` and advances without executing acceptance again.

## Stale-attempt recovery

A persisted `TESTED_GREEN` attempt can resume when the same immutable candidate is already accepted/current. Recovery is read-only and must reach:

```text
TESTED_GREEN
→ ACCEPTED
→ ADOPTED_CURRENT
→ FINAL_VERIFIED
```

without a second `accept-candidate` invocation.

## Structural current-state verification

`ADOPTED_CURRENT` no longer searches serialized JSON for version/SHA substrings. It structurally requires the exact repository entry, artifact/source refs and versions, and `registry_current.sha256` to match the immutable attempt.

## Canonical command

```bash
pb release run \
  --artifact chatgpt_claudecode_workflow-2_v0.1.125.3.3.zip \
  --version v0.1.125.3.3 \
  --baseline-version v0.1.125.3.2 \
  --release-type repair \
  --profile full \
  --test-timeout 3600 \
  --until final-verified \
  --adopt \
  --json
```

Git commit, Git push, and Project Source upload remain disabled unless explicitly authorized.
