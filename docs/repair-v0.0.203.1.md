# Repair v0.0.203.1

Base release: v0.0.203
Repair version: v0.0.203.1

## Reason

The v0.0.203 full validation did not adopt because the browser integration source-overwrite regression classified a second upload of the same file as a fresh add. The upload persisted, but the result reported `already_exists=false`, `overwritten=false`, and `removed_existing=false`.

## Files changed

- `promptbranch_browser_auth/client.py`
- `chatgpt_browser_auth/client.py`
- `tests/test_project_source_capabilities.py`
- `README.md`
- `UPGRADING.md`
- version metadata and versioned test expectations

## Repair

File-source overwrite detection now uses a bounded pre-upload presence probe when the initial source-card snapshot does not find the expected file source. This avoids treating a stale or briefly empty Sources tab snapshot as authoritative before overwrite upload.

## Validation performed

- Python compile checks for modified Python modules
- Focused project source capability tests
- CLI/parser/container/MCP/version tests
- ZIP CRC/testzip verification
- ZIP hygiene verification

## Scope confirmation

No MVP-F scope was advanced. This repair does not add ZIP verification, candidate migration, Project Source mutation automation, or artifact adoption behavior. It only repairs source-overwrite detection/test correctness for the intended v0.0.203 release.
