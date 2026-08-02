# Promptbranch v0.1.117

## Slice

PBAI compliance inventory and evidence-bound generic release pipeline.

## Baseline

Accepted/current `v0.1.116`, artifact `chatgpt_claudecode_workflow-2_v0.1.116.zip`, assigned Project Source `chatgpt_claudecode_workflow-2_v0.1.116(1).zip`, SHA-256 `1349f162b37834fccd4e35b2fe56b72003f22ddc406db55dead43bb85d221dc8`.

## Delivered in the candidate

- `pb application architecture inventory` inventories PBAI migration, proof level and release-contract readiness across repeated repository paths without mutation.
- `pb release pipeline plan` emits a read-only ordered pipeline and all dependency blockers.
- `pb release pipeline apply` runs repository-owned validate/test/build/verify operations and enables later mutations only through explicit flags.
- Git commit requires explicit `--stage-all --commit`; push requires same-run commit.
- Project Source publication requires same-run push.
- Adoption requires exact same-run source evidence with assigned filename and immutable backing identifiers.
- Accepted/current verification requires same-run adoption and checks the selected repository state.
- The artifact is rebuilt and reverified after the release commit before publication.
- Pipeline evidence is written beneath the repository-declared ignored evidence directory.
- `release_pipeline` is a mandatory deterministic release-validation group and is selected by the impact map when pipeline, lifecycle, publication, adoption or current-state code changes.
- The tracked release contract invokes `scripts/run-release-validation-groups.py` instead of raw repository-root `pytest`, keeping the authoritative gate bounded to deterministic repository-owned groups.
- Accepted/current verification binds the exact backend-assigned Project Source filename, registry current artifact and version, and state/registry consistency from the same release run.

## Safety boundary

Plan mode is read-only. Apply requires exact canonical `--confirm-version`. A failed phase prevents every dependent later phase. No Project Source publication, adoption, Git commit, or Git push is performed by candidate construction or focused validation.

## Next releases

- `v0.1.118` — resumable/importable pipeline evidence and recovery after partial failure.
- `v0.1.119` — read-only multi-repository release-set dependency planning.
- `v0.1.120` — guarded multi-repository rollout execution and rollback evidence.

## Acceptance boundary

Focused deterministic release groups, executable PBAI inventory, sandbox and execution-envelope gates pass in the candidate workspace. Candidate construction does not adopt the release. Strict host/direct, localhost, external-live, final Artifact Guardian, publication, adoption, accepted/current verification and operational evidence remain required.
