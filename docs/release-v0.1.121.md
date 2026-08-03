# Release v0.1.121 — Resumable release-set rollout recovery and operator reconciliation

## Scope

Extend the guarded `v0.1.120` release-set rollout with deterministic recovery from an interrupted process or incomplete reverse rollback. Recovery is always based on an existing atomic checkpoint, the original release-set and plan identity, the exact pre-rollout current identities, and a new read-only reconciliation digest computed from authoritative project registry state.

## Commands

```bash
pb release set reconcile \
  --repo-path /path/to/coordinator-repo \
  --manifest .promptbranch-release-set.json \
  --evidence <checkpoint-summary-or-evidence-directory> \
  --json

pb release set resume \
  --repo-path /path/to/coordinator-repo \
  --manifest .promptbranch-release-set.json \
  --evidence <checkpoint-summary-or-evidence-directory> \
  --confirm-release-set-id <release_set_id> \
  --confirm-plan-sha256 <original_plan_sha256> \
  --confirm-reconciliation-sha256 <latest_reconciliation_sha256> \
  --execute \
  --rollback-on-failure \
  --stage-all --commit --push --publish --adopt --verify-current \
  --json
```

## Read-only reconciliation

`pb release set reconcile` does not write the checkpoint, repositories, Git, Project Sources, registry, or accepted/current state. It:

- validates the checkpoint event chain and any existing terminal evidence hash;
- rebuilds the manifest and target artifact plan;
- reconstructs the original plan digest using the checkpoint's exact pre-rollout current identities, so already completed repository adoption does not invalidate recovery binding;
- reads authoritative current artifact and Project Source identity for every repository;
- classifies each repository as `target_current`, `previous_current`, `missing_current`, or `ambiguous_current`;
- emits pending forward order and reverse rollback order;
- selects exactly one recovery mode;
- emits a canonical `reconciliation_sha256` that binds the checkpoint bytes, original plan, observed identities, and selected recovery mode.

Recovery modes:

```text
continue_rollout
resume_rollback
finalize_success
finalize_rollback
already_terminal
blocked
```

Any repository current identity that matches neither the exact pre-rollout identity nor the exact release-set target produces `release_set_operator_reconciliation_required` and blocks automatic mutation.

## Guarded resume

`pb release set resume` recomputes reconciliation immediately before mutation and requires exact confirmation of:

- `release_set_id`;
- the original plan SHA-256;
- the latest reconciliation SHA-256;
- the complete release-pipeline mutation envelope.

The resume path:

- never replays a repository already verified at the exact target identity;
- continues only repositories still at their exact pre-rollout identity;
- resumes rollback only for repositories still at the target identity, in reverse dependency order;
- accepts an operator-repaired incomplete rollback only after every repository is authoritatively back at its exact pre-rollout artifact and Project Source identity;
- finalizes a crash that happened after all target identities were reached but before terminal evidence was written;
- appends hash-chained resume and reconciliation events to the existing evidence;
- records `resume_history`, `resume_count`, the prior evidence SHA-256 where present, and the exact reconciliation used for each resume;
- rewrites checkpoint and terminal summary atomically.

A resumed rollout that later fails retains the original automatic rollback requirement. The final status remains one of:

```text
release_set_rollout_verified
release_set_rollout_failed_rollback_verified
release_set_rollout_failed_rollback_incomplete
```

## Evidence contracts

- `promptbranch.release_set.rollout.evidence` remains schema version `1.0` and now permits resume history and the last reconciliation record.
- `promptbranch.release_set.rollout.reconciliation` schema version `1.0` defines the read-only operator reconciliation payload.
- `pb release set evidence-validate` continues to validate the complete event hash chain and final evidence SHA-256 after resumed execution.

## Out of scope

- automatic selection of an operator override for ambiguous repository state;
- modification of a release-set manifest during recovery;
- replay of already verified Git, Project Source, adoption, or current-state mutations;
- parallel repository mutation inside a dependency wave;
- ChatGPT Project deletion.

The next planned slice is `v0.1.122 — Bounded parallel release-set wave execution and concurrency evidence`.
