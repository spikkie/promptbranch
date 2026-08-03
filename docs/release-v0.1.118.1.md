# Promptbranch v0.1.118.1

## Purpose

Repair the release-integrity gap exposed by the interrupted and rerun `v0.1.118` lifecycle: identical committed source produced different canonical ZIP bytes, and a full rerun republished the same version under a new indexed Project Source identity instead of resuming prior evidence.

## Changes

- Canonical artifacts are always rewritten by the repository-owned deterministic builder.
- ZIP entries use fixed ordering, timestamp, Unix mode metadata and `ZIP_STORED` bytes; filesystem mtimes and zlib behavior cannot change the release hash.
- Release control rebuilds the canonical archive twice and requires byte-identical output.
- A crash-consistent release-control checkpoint binds repository, version, artifact SHA-256, Git commit and release-contract SHA-256 before source mutation.
- Successful Project Source publication records a provisional immutable identity with assigned filename, processed file id and Library metadata id.
- Exact reruns import the checkpoint and skip source upload; drift fails before source mutation.
- Adoption/current verification finalizes the same checkpoint.

## Safety

This is a repair release. It does not advance the normal roadmap, grant new mutation authority, alter Project deletion policy, or change accepted/current state before strict adoption.

## Next normal slice

`v0.1.119 — Read-only multi-repository release-set dependency planner`.
