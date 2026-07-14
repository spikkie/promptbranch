# Repair v0.1.103.10.109 — deterministic capacity pruning before Project Source upload

## Problem

The Plus-plan Project Source surface is limited to 25 files. With 25 visible sources, the upload dialog could open but no upload request or processing stream started. Promptbranch then waited for persistence and returned the misleading `persistence_not_verified` status. Existing capacity code also failed to parse long Promptbranch versions and backend-indexed names such as `v0.1.103.10.106(1).zip`.

## Repair

- Read and stabilize the authoritative Project Sources surface before upload.
- Apply capacity pruning only when the authoritative count is at least 25.
- Parse canonical and backend-indexed release ZIPs with arbitrary-length dotted versions.
- Select exactly one oldest eligible release source from the requested repository family.
- Resolve the accepted/current version and filename from the project artifact registry, with the validated project control surface as a read-only fallback.
- Exclude both the requested candidate and the accepted/current release; fail closed when the accepted/current identity cannot be resolved.
- Remove the selected source by exact identity with no loose retry.
- Require an authoritative count transition from 25 to 24 and prove the selected source disappeared.
- Upload the candidate exactly once and retain the processing-stream assigned-name verification from v0.1.103.10.107.
- Require the final authoritative source count to return to 25.
- Return `source_capacity_reached` immediately when no safe prune candidate exists; do not open the upload dialog or wait for persistence.

## Required diagnostics

```json
{
  "capacity_limit": 25,
  "capacity_before": 25,
  "capacity_pruned": true,
  "capacity_pruned_source": "chatgpt_claudecode_workflow-2_v<obsolete-version>.zip",
  "capacity_after_prune": 24,
  "upload_started": true,
  "persistence_verified": true,
  "capacity_after_upload": 25
}
```

## Preserved boundaries

- v0.1.103.10.108 singleton canonical/indexed family replacement remains unchanged.
- No documentation or unrelated repository source is eligible for automatic pruning.
- No Project Source mutation, adoption, project deletion, Git commit, or Git push is performed while building this candidate.
