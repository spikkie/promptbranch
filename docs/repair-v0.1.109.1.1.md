# Repair v0.1.109.1.1

## Candidate

`v0.1.109.1.1 — Tracked repository Project binding and runtime evidence separation`

## Baseline

Accepted/current remains `v0.1.109`. The `v0.1.109.1` candidate was not adopted because both full transports failed the same authority test while the repository was correctly joined.

## Root cause

`repository.project_identity` was classified as runtime-only even though `.promptbranch-repo.json` contains stable, portable, non-secret repository configuration. Clean ZIP tests omitted the file while release validation ran in a joined checkout where the file existed, producing environment-dependent authority status.

## Repair

- Track `.promptbranch-repo.json` in Git and include it in release ZIPs.
- Make it required static repository authority.
- Keep project membership and adopted artifact/source evidence user-local.
- Make `pb project join --repo-root .` rebuild local membership from the tracked file.
- Reject explicit join arguments that conflict with tracked authority.
- Import the tracked file from candidate ZIPs rather than preserving a stale checkout copy.
- Add migration, fresh-clone, extracted-ZIP, accidental-deletion, mismatch, and ZIP-inclusion coverage.

## Scope boundary

No change to artifact adoption evidence, exact assigned Project Source identity, processed-file IDs, Library metadata IDs, remote Project Settings, or Project deletion policy.
