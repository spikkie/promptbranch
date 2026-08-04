# Release v0.1.123 — Canonical MVP proof cycle 1

## Purpose

Execute the first clean normal MVP proof cycle from accepted/current repair baseline `v0.1.122.1`. This release is scope-frozen: it adds no new platform capability and exists to produce explicit canonical evidence for the end-to-end Promptbranch workflow.

## Required proof

1. Parse a valid Promptbranch reply envelope and perform real artifact intake.
2. Download and verify `chatgpt_claudecode_workflow-2_v0.1.123.zip`.
3. Pass strict release control 10/10 with zero outer skips.
4. Verify the visual artifact ZIP roundtrip.
5. Publish and bind the exact Project Source identity.
6. Adopt and verify accepted/current `v0.1.123`.
7. Bind candidate, intake, adoption, and current SHA-256 values exactly.
8. Issue one protocol continuation Ask from accepted `v0.1.123` toward `v0.1.124`.
9. Emit `mvp_proof_cycle_passed`.

## Fail-closed rule

Missing intake, stale baseline, repair-version identity, any failed or skipped outer gate, SHA-256 mismatch, adoption/current mismatch, or continuation mismatch prevents the proof from counting. No continuation Ask is issued before preflight succeeds.

## MVP state

```text
accepted/current before validation: v0.1.122.1
formal proof count before validation: 0/2
this candidate: v0.1.123 — cycle 1
next after successful proof: v0.1.124 — cycle 2 and final verdict
```

## Operator commands

```bash
python3 scripts/run-release-validation-groups.py --repo . --json
python3 promptbranch_artifact_guardian.py --repo . --zip chatgpt_claudecode_workflow-2_v0.1.123.zip --version v0.1.123 --json
```

After strict adoption and real candidate intake:

```bash
scripts/finalize-mvp-proof-cycle.sh \
  --cycle 1 \
  --version v0.1.123 \
  --baseline-version v0.1.122.1 \
  --next-version v0.1.124 \
  --artifact-intake "$HOME/tmp/v0.1.123.artifact-intake.json"
```
