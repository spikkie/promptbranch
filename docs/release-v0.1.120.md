# Release v0.1.120 — Guarded multi-repository rollout execution and rollback evidence

## Scope

Consume only a compatible, locally verified and SHA-256-bound `promptbranch.release_set` plan. Execute each repository through its generic release pipeline in deterministic dependency order. Require exact release-set and plan-digest confirmation, complete Git/publication/adoption/current-verification authorization, and automatic rollback-on-failure.

## Commands

```bash
pb release set plan \
  --repo-path /path/to/coordinator-repo \
  --manifest .promptbranch-release-set.json \
  --json

pb release set apply \
  --repo-path /path/to/coordinator-repo \
  --manifest .promptbranch-release-set.json \
  --confirm-release-set-id <release_set_id> \
  --confirm-plan-sha256 <plan_sha256> \
  --execute \
  --rollback-on-failure \
  --stage-all --commit --push --publish --adopt --verify-current \
  --json

pb release set evidence-validate \
  --evidence <release-set-rollout-summary.json-or-directory> \
  --json
```

## Guardrails

- The plan is recomputed immediately before mutation.
- `release_set_id` and `plan_sha256` confirmations must match exactly.
- Every target ZIP must be locally verified, canonical, VERSION-consistent and SHA-256-bound.
- Every repository executes through `pb release pipeline apply` with the complete guarded lifecycle.
- Execution follows dependency waves and deterministic repository order within each wave.
- Before mutation, accepted/current artifact and Project Source identities are captured for every target repository.
- Any repository failure stops later execution.
- Successfully completed repositories are rolled back in reverse completion order through the repository-owned `rollback` operation in `.promptbranch-release.json`.
- Rollback must restore the exact previous version, artifact SHA-256 and Project Source identity; otherwise the result is `release_set_rollout_failed_rollback_incomplete`.
- Checkpoints are atomically written after every transition.
- Event records form a SHA-256 hash chain. The final evidence object has its own canonical SHA-256 and is independently validated by `evidence-validate`.

## Repository rollback contract

`operations.rollback` is repository-owned and may not invoke a shell. Promptbranch passes the exact pre-rollout identity using these environment variables:

```text
PROMPTBRANCH_RELEASE_SET_ID
PROMPTBRANCH_RELEASE_SET_PLAN_SHA256
PROMPTBRANCH_ROLLBACK_REPO_ID
PROMPTBRANCH_ROLLBACK_VERSION
PROMPTBRANCH_ROLLBACK_ARTIFACT
PROMPTBRANCH_ROLLBACK_SHA256
PROMPTBRANCH_ROLLBACK_SOURCE_REF
PROMPTBRANCH_ROLLBACK_PROCESSED_FILE_ID
PROMPTBRANCH_ROLLBACK_LIBRARY_METADATA_ID
PROMPTBRANCH_ROLLBACK_PROJECT_ID
```

The Promptbranch repository supplies `scripts/rollback-release-artifact.py`, which reconstructs evidence for the exact prior Project Source and invokes evidence-bound adoption.

## Out of scope

- parallel mutation inside one wave;
- automatic continuation after an interrupted process;
- operator reconciliation of an incomplete rollback;
- ChatGPT Project deletion;
- implicit deployment commands outside repository release contracts.

The next planned slice is `v0.1.121 — Resumable release-set rollout recovery and operator reconciliation`.
