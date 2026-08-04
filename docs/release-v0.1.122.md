# Promptbranch v0.1.122

## Release type

Normal release — canonical MVP proof cycle 1.

## Baseline

- Accepted/current version: `v0.1.121.1`
- Accepted/current artifact: `chatgpt_claudecode_workflow-2_v0.1.121.1.zip`
- Accepted/current SHA-256: `733be42b0ff0fe9afec64d038cfc49f7440217944f38dca94276129b5b38ebdc`

## Purpose

This release freezes product scope and turns the canonical MVP completion rule into an explicit evidence contract. A generic green release is not sufficient. Cycle 1 passes only when the same normal release has evidence for real artifact intake, deterministic validation, live attachment transport, adoption, accepted/current identity, and a continuation protocol ask from the newly adopted baseline.

Bounded parallel release-set wave execution is intentionally deferred until after the MVP verdict.

## Changes

- Added `promptbranch_mvp_proof.py`, a read-only evaluator for one canonical MVP proof cycle.
- Added `scripts/verify-mvp-proof-cycle.py` for deterministic evidence verification and canonical proof SHA-256 generation.
- Added `scripts/finalize-mvp-proof-cycle.sh` to issue the post-adoption continuation ask and evaluate cycle evidence.
- Added regressions proving missing download evidence, repair versions, stale continuation baselines, failed/skipped release gates, or incomplete transport evidence fail closed.
- Added the proof evaluator tests to the mandatory `release_pipeline` validation group.
- Updated project authority, DoD, decision, migration, release and horizon records for proof cycle 1.

## Mutation boundary

The evaluator is read-only. It does not:

- publish or remove Project Sources;
- adopt artifacts;
- commit or push Git changes;
- mutate repositories;
- run deployments;
- delete ChatGPT Projects.

The finalization wrapper issues one protocol ask after adoption but delegates all release mutation to the existing strict release-control lifecycle.

## Cycle-1 evidence contract

The proof requires:

1. an artifact intake record with `download_performed=true` and `verification_performed=true`;
2. a strict all-tests summary with 10/10 GO, zero failures and zero skips;
3. successful visual artifact smoke ZIP transport evidence;
4. successful adoption evidence for `v0.1.122`;
5. accepted/current evidence for the exact artifact;
6. a continuation ask whose baseline is `v0.1.122` and target is `v0.1.123`.

## Acceptance boundary

The candidate is not accepted/current and cycle 1 is not complete until strict host release control and `scripts/finalize-mvp-proof-cycle.sh` both succeed. If `v0.1.122` requires a repair, the consecutive normal-release proof count remains zero.

## Next

`v0.1.123 — Canonical MVP proof cycle 2 and final MVP verdict`.

## Post-release outcome

Strict host release validation and adoption passed, making `v0.1.122` accepted/current with SHA-256 `e552438231227a3f190f8ad4930f01d6c11ff6c1079372228e4634128de0812e` and Project Source `chatgpt_claudecode_workflow-2_v0.1.122(1).zip`.

Formal proof cycle 1 was not counted. Finalization exposed defects in project-level current parsing, SHA-256 evidence binding, pre-continuation preflight ordering, and wrapper exit handling. These are repaired in `v0.1.122.1`; the next clean normal proof sequence is `v0.1.123` then `v0.1.124`.
