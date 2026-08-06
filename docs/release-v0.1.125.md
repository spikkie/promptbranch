# v0.1.125 — Canonical PB environment proof cycle 2 and final control-plane verdict

Status: candidate built from accepted/current artifact baseline `v0.1.124`; validation and explicit candidate acceptance remain required.

## Purpose

Repeat the complete PB candidate lifecycle from the accepted `v0.1.124` baseline and issue the final control-plane proof verdict. This release continues developing and testing Promptbranch itself. It does not start external application development.

## Consolidated implementation baseline

The normal release carries forward the PB runtime corrections proven during the `v0.1.123.2.6` repair line:

- exact request/message/answer correlation for rendered attachment discovery;
- authenticated browser-context artifact download;
- legacy persisted protocol-record normalization;
- post-materialization reply finalization and exact inbox reuse;
- exact validated-run migration and candidate-run identity preservation;
- envelope SHA-256, size, entry-count, CRC, filename, and embedded-version checks;
- `pasted.txt` backend filename handling for pasted text sources while preserving strict uploaded-file filename checks;
- fail-closed candidate testing and explicit acceptance semantics.

These repairs are consolidated into the normal release so a future installed `v0.1.125` runtime does not regress to the pre-proof implementation.

## Mandatory documentation included

- `docs/project/pb-environment-vs-application-development.md`
- `docs/project/pb-mvp-roadmap-v0.1.124.md`
- updated `docs/project/plan.md`, `status.md`, `release-status.md`, `slice-horizon.md`, `plan-state.json`, `architecture.md`, `mvp.md`, and `decisions.md`
- updated draw.io architecture sources with the `v0.1.125–v0.1.134` roadmap and the System A/System B boundary

## Required proof after candidate construction

1. Exact accepted/current `v0.1.124` baseline.
2. One pinned release request and exact response correlation.
3. Exactly one real `v0.1.125` ZIP candidate.
4. Verified SHA-256, size, entry count, embedded version, layout, and hygiene.
5. Mandatory candidate test profile with a non-truncating timeout.
6. Explicit `accept-candidate` gate.
7. `pb artifact current --json` alignment.
8. `pb artifact candidate-run --json` returns lifecycle complete.
9. No manual candidate-file or state repair between canonical lifecycle steps.

## Exclusions

No external application source mutation, application artifact acceptance, production deployment, Project deletion, broad autonomous execution authority, Project Source mutation, Git commit, or Git push is performed by candidate construction.
