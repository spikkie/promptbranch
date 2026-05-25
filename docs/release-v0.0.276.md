# Release v0.0.276

Base: `chatgpt_claudecode_workflow_v0.0.275.zip`

## Scope

Focused fix for `pb artifact candidate-next` stale accepted candidate filtering.

## Changes

- Keep historical/accepted candidates visible in candidate inventory.
- Prevent unscoped `pb artifact candidate-next` from selecting `candidate_already_accepted` rows as actionable candidates.
- Return `candidate_next_no_actionable_candidate` with no command when the registry contains only historical/non-actionable candidates.
- Prevent candidate inventory from recommending repair/remigration when only accepted historical candidates remain.
- Preserve scoped adopted-current fallback behavior for explicit candidate-run validation.

## Non-goals

- No artifact intake, source upload, adoption, Git, browser automation, or write-capable MCP changes.
- No candidate registry cleanup/migration. Historical records are reported, not deleted.

## Validation

- `pytest -q tests/test_promptbranch_cli.py -k "candidate_next or candidate_run or mvp_status"`
- focused regression: stale accepted `v0.0.259` candidate with missing ZIP while current baseline is newer remains inventory-only and is not selected.
