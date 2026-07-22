# Promptbranch plan at v0.1.105

## Baseline authority

```text
accepted/current artifact: chatgpt_claudecode_workflow-2_v0.1.104.5.zip
accepted/current version:  v0.1.104.5
validation:                10/10 GO
adoption:                  release_adopted_and_verified
```

The `v0.1.104` repair sequence is complete. Its accepted authority proves the sandbox mutation/validation/rollback contract, mandatory 13-gate release check, current-turn browser readiness, parse-independent visual completion, fresh direct and independent localhost validation, hermetic offline pytest isolation, and evidence-bound adoption.

## Active slice

### v0.1.105 — Sandbox correction promotion readiness check

This slice assesses evidence only. It does not promote correction workflows and does not grant new write authority.

The operator command is:

```bash
pb loop promotion-readiness \
  --target examples/loop-targets/sandboxed-file-mutation-target.json \
  --runs 3 \
  --json
```

Required assessment sequence:

```text
validate target
  -> execute the existing sandbox-only proof in temporary workspace 1
  -> execute the same proof in temporary workspace 2
  -> execute the same proof in temporary workspace 3
  -> require every run to contain complete exact evidence
  -> canonicalize deterministic evidence only
  -> require one identical SHA-256 fingerprint across all runs
  -> require three distinct temporary workspace identities
  -> emit ready, not_ready, or blocked
  -> stop without granting broader authority
```

### Status meanings

- `ready`: all three evidence runs are complete, deterministic, independently sandboxed, and preserve every safety invariant. This permits only the planned `v0.1.106` GO/NO-GO decision record.
- `not_ready`: the assessment executed, but evidence is incomplete, contradictory, non-deterministic, or violates a safety invariant. Remain sandbox-only.
- `blocked`: the assessment cannot be performed safely, including invalid target, invalid run count, missing evidence runs, or execution failure. Stop for operator review.

## Mandatory evidence

Every run must prove:

- exact `promptbranch.loop.sandbox_mutation_verification` schema and terminal status;
- all 13 existing sandbox gates passed;
- exact before and after hashes;
- one allowlisted read-only validation command passed without mutation;
- rollback restored the exact before snapshot;
- repository fixture remained unchanged;
- temporary workspace was deleted;
- no repository, deployment, Kubernetes, Project Source, artifact-adoption, or Project-deletion authority was exercised.

Dynamic temporary workspace names are excluded from the deterministic fingerprint, but three distinct workspace identities are mandatory.

## Authority boundary

A `ready` result is not a promotion decision. It records:

```text
promotion_decision_recorded: false
broader_mutation_authority_granted: false
repository_mutation_authority_granted: false
deployment_authority_granted: false
project_source_mutation_authority_granted: false
artifact_adoption_authority_granted: false
chatgpt_project_deletion_authority_granted: false
```

## Next slices

- `v0.1.106 — Controlled correction promotion decision record`
- `v0.1.107 — Controlled correction execution envelope design`

No correction may move beyond copied temporary sandbox fixtures before an explicit `v0.1.106` GO decision.
