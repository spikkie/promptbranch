# v0.1.126.1 — whole-release publication convergence repair

Baseline authority remains accepted/current `v0.1.125.3.4.2`. This repair is constructed from immutable candidate `v0.1.126` SHA-256 `7945f176276b94fe30b25916219d05515575226cb39ea160532f1abcf449ec1e`.

## Live blocker repaired

The first `v0.1.126` canonical full run validated the isolated candidate 53/53 but stopped at `RUNTIME_PREPARED` with `BLOCKED_RETRYABLE / optional_publication_failed`. Evidence proved that the Git working tree still resolved as `v0.1.125.2`, while the tested source was `v0.1.126`. Project Source upload returned exit code 0 and the rendered source `chatgpt_claudecode_workflow-2_v0.1.126(1).zip` existed, but the state machine selected a nested lock JSON object and reported a false failure.

## Repair invariants

- Full release-source fingerprint replaces the old three-file source fingerprint.
- After candidate validation and before Git publication, the exact immutable candidate is re-extracted and materialized into the working tree while `.git`, `.pb_profile`, environment/generated and browser-debug state are preserved.
- `tested_source_fingerprint == materialized_worktree_fingerprint == committed_tree_fingerprint` is release-blocking.
- Git commit is executed through the guarded release pipeline; Git push is separately timed and verified against the configured upstream.
- Publication stdout/stderr are retained as hashed files and authoritative command results are selected from complete top-level JSON documents by action.
- Project Source publication lists/reconciles the displayed filename family, including ChatGPT-assigned `(N)` suffixes; ambiguous successful upload results are reconciled against the rendered source surface.
- A retry of the same immutable attempt may reuse cryptographically verified green candidate-test evidence instead of rerunning the full suite.
- ETA history schema 1.1 models `CANDIDATE_TEST`, `WORKTREE_MATERIALIZE`, `GIT_COMMIT`, `GIT_PUSH`, and `PROJECT_SOURCE_UPLOAD` subphases. ETA remains advisory only.

## Acceptance

`v0.1.126.1` is not accepted by construction. It closes the `v0.1.126` normal-slice DoD only after the canonical full live run reaches `FINAL_VERIFIED`, independent all-state verification is green, the exact tested image is promoted to production, Git commit/push are verified, and the exact release ZIP is reconciled in Project Sources.
