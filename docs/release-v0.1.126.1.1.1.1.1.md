# v0.1.126.1.1.1.1.1 — Runtime fingerprint publication authority repair

## Authority

- Built from the exact immutable `v0.1.126.1.1.1.1` artifact (`a2b669b51de6a8d3c0ed95832acdf421b003b47533dfd87566fa6b76f27741cb`).
- Accepted/current baseline remains `v0.1.125.3.4.2` until this candidate reaches `FINAL_VERIFIED`.
- Release mode: repair; no normal-slice scope advance.

## Live failure repaired

The `v0.1.126.1.1.1.1` exact candidate passed the complete canonical 53-unit validation suite. Publication then failed before any worktree/Git/Project Source mutation with `worktree_materialization_precondition_failed`. Runtime preparation had already computed and persisted the canonical source fingerprint in `runtime-checkpoint.json`, but the `RUNTIME_PREPARED` evidence projection omitted that field. Publication consumers independently read the missing projection and therefore observed an empty expected fingerprint.

## Repair

- The persisted runtime checkpoint is the authoritative runtime source-fingerprint store.
- `prepare_runtime` explicitly projects the checkpoint fingerprint into `RUNTIME_PREPARED` evidence.
- One `_runtime_source_fingerprint` accessor validates checkpoint authority and projection equality.
- Worktree materialization and Git committed-tree identity guards consume that accessor rather than reading the projection directly.
- Missing checkpoint/projection identity fails as `runtime_source_fingerprint_missing`.
- Checkpoint/projection disagreement fails as `runtime_source_fingerprint_disagreement`.
- `RUNTIME_PREPARED` independent verification requires the projected fingerprint to equal the persisted checkpoint fingerprint.

## Acceptance

Construction validation does not accept this release. The exact candidate must pass canonical candidate validation and then prove the previously blocked publication chain: tested source → worktree materialization → Git commit/tree fingerprint → push → Project Source upload → acceptance → production promotion → `FINAL_VERIFIED`.
