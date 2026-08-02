# Promptbranch v0.1.118

## Slice

Resumable/importable release-pipeline evidence and recovery.

## Baseline

Accepted/current `v0.1.117.1`, canonical artifact `chatgpt_claudecode_workflow-2_v0.1.117.1.zip`, assigned Project Source `chatgpt_claudecode_workflow-2_v0.1.117.1(1).zip`, SHA-256 `44c18b9248bf1e2add7af3e2a156ff21204bb59954f14159f334a09343735719`.

## Delivered in the candidate

- Every pipeline run atomically writes a crash-consistent `release-pipeline-checkpoint.json` before execution and after every phase.
- Checkpoints and final summaries bind repository id, canonical version, artifact filename/SHA-256, Git commit and release-contract SHA-256.
- `pb release pipeline import --evidence <path>` validates a checkpoint, summary or evidence directory without mutation and identifies completed, failed, first-incomplete and reusable mutation phases.
- `pb release pipeline resume --evidence <path>` creates a new recovery run with explicit imported provenance, reused phases, replayed safe phases and final recovery status.
- Repository-owned validate/test/build/verify gates are rerun during recovery.
- Successful Git commit/push and Project Source publication phases are reused only with exact immutable proof; they are not replayed.
- Imported Project Source evidence is copied into the recovery run and remains the exact adoption input.
- Successful imported adoption/current evidence is reconciled against authoritative current state. If it no longer matches, automatic replay is forbidden and recovery fails closed.
- Legacy `v0.1.117` pipeline summaries can be imported when their phase-specific artifact, Git and source bindings are sufficient. Missing immutable bindings block reuse.

## Safety boundary

Import is read-only. Resume still requires canonical `--confirm-version`; its explicit mutation flags must exactly match the imported run so recovery cannot silently narrow or expand authority. Imported evidence never independently advances accepted/current state. Unsupported evidence schema, artifact hash mismatch, contract drift, Git HEAD mismatch, missing push proof, mutation-envelope mismatch, missing exact source hash, ambiguous source identity or adopted/current divergence blocks before remote mutation. Project deletion remains frozen.

## Validation boundary

Focused recovery simulations, authority validation, test-suite validation and all 14 deterministic release groups pass locally before packaging. Strict host direct, localhost, external-live, Artifact Guardian, Project Source publication, adoption, accepted/current verification and operational evidence remain required before acceptance.

## Next release

`v0.1.119 — Read-only multi-repository release-set dependency planner`.
