# Release v0.1.120.1 — Checkpoint resume exit-code handling repair

## Purpose

Repair the strict release-control retry path exposed after `v0.1.120` failed external-live validation. The existing checkpoint preflight correctly returned code `10` to mean that the exact provisional artifact and Project Source identity must be reused, but the helper re-enabled Bash `errexit` before returning that non-zero control code. The workflow therefore terminated before its caller could interpret the resume result and start validation.

## Changes

- Remove the inner `set -e` from `release_control_checkpoint_preflight`.
- Keep `set +e` / result capture / `set -e` ownership in the existing caller.
- Preserve checkpoint result `10` as a successful source-reuse branch.
- Preserve the exact previously assigned source filename, processed file ID, Library metadata ID and artifact SHA-256 on retry.
- Add an executable regression that extracts the real checkpoint function from release control, runs it with a helper returning `10`, and proves the caller reaches the source-reuse and test-execution markers.
- Include the checkpoint regression in the mandatory `release_pipeline` validation group.

## Safety

This is a repair release. It does not advance the normal roadmap, alter release-set execution or rollback semantics, grant additional mutation authority, delete Projects, or adopt any artifact without the unchanged strict validation gate.

## Baseline and next slice

- Accepted/current remains `v0.1.119` until strict adoption evidence proves this repair.
- `v0.1.120` is repair-required and must never be adopted from its original bytes.
- The next normal slice after repair acceptance remains `v0.1.121 — Resumable release-set rollout recovery and operator reconciliation`.
