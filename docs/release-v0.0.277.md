# Release v0.0.277

Base artifact: `chatgpt_claudecode_workflow_v0.0.276.18.zip`
Release type: normal incremental release

## Change summary

- Added automatic Project Source capacity pruning for versioned release ZIP uploads.
- When a file source upload starts and the Sources tab already contains 25 sources, Promptbranch now detects same-family release ZIPs and removes the lowest version before opening the upload dialog.
- The pruning selector is intentionally narrow: it only acts on canonical versioned `.zip` release artifacts with the same filename prefix/suffix family as the requested upload.
- The add result now reports `capacity_pruned`, `capacity_prune_result`, and keeps `removed_existing` true when the source limit was cleared by a verified prune.

## Risk controls

- Does not prune arbitrary text/link sources.
- Does not prune unrelated release families such as `ib_forex_trading.*.zip` when uploading `chatgpt_claudecode_workflow_*.zip`.
- Uses the existing verified source removal path, including exact matching first and anchored fallback only after exact removal times out.
- Fails closed with `source_limit_no_matching_release_prune_candidate`, `source_limit_prune_remove_failed`, or `source_limit_prune_not_verified` instead of deleting unrelated sources.

## Validation

- `python3 -m pytest tests/test_project_source_capabilities.py -q`
- `python3 -m compileall promptbranch_browser_auth chatgpt_browser_auth promptbranch_automation chatgpt_automation promptbranch_cli.py promptbranch_container_api.py`
