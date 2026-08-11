# v0.1.128.1 — Single authority for Promptbranch release artifacts

## Baseline

Accepted/current baseline is FINAL_VERIFIED `v0.1.128` with artifact SHA-256 `5d1d64e8d146a3bf58f388149d6a917982239c1dbb9e2f5256f3ef33ba9abaac`. This repair does not rewrite v0.1.128 and does not advance external-application scope.

## Repair scope

- Enforce `(repo_id, version) -> exactly one immutable SHA-256` across release/adopt lifecycle kinds.
- Import verified release bytes into the project-scoped SHA-addressed Promptbranch object authority.
- Treat filenames and external filesystem locations as metadata/input, not identity.
- Make explicit `--local-path` strict: missing paths fail without same-name fallback.
- Make release→adopt a lifecycle transition on one immutable object; `current` selects adopted identity only.
- Make `artifact current` verify object SHA and state/source projection without hidden reconstruction.
- Extend `repo doctor` with release-identity uniqueness, object existence/SHA/ownership, and state projection checks.
- Preserve Project Source as publication evidence and preserve the external-repository version/runtime-domain distinction.
- Add `scripts/run-release-lifecycle-proof.py`, a resumable wrapper around the existing canonical release state machine that independently verifies each reached state and performs a final scoped current proof using the launcher Python and tracked repo identity.

## Non-goals

No new lifecycle states, publication provider, Git/GitHub behavior, migration framework, legacy compatibility shim, or external-application feature is introduced. Existing conflicting registries fail closed and require an explicit cleanup decision.

## Closure

Construction requires all canonical validation groups, deterministic exact-ZIP proof, and Artifact Guardian. Live closure additionally requires a controlled artifact-authority flow including a deliberate conflicting-SHA rejection and one canonical v0.1.128.1 lifecycle to independently verified `FINAL_VERIFIED` with fresh scoped current alignment.
