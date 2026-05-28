# Repair release v0.0.278.12

Base release: v0.0.278.11
Repair version: v0.0.278.12

## Reason

v0.0.278.11 made old-task DOM diagnostics cheap/capped by default, but old-task evidence still showed successful asks spending tens of seconds in `after_submit_composer_snapshot_seconds` even with `after_submit_snapshot_mode=post_submit_minimal`.

## Scope

This repair keeps the v0.0.278.9 submit accounting invariant and the v0.0.278.11 capped DOM diagnostics, while skipping post-submit composer snapshots on successful confirmation fast paths. Composer snapshots are captured only when submit confirmation fails or when explicit deep-debug snapshot mode is enabled.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `docker-compose.chatgpt-service.yml`
- `promptbranch_browser_auth/client.py`
- `tests/test_project_list_browser_client.py`
- version assertion tests under `tests/`
- `docs/repair-v0.0.278.12.md`

## Behavior

- Successful button submits no longer call the post-submit composer snapshot by default.
- Successful Enter fallback submits also skip the snapshot unless deep-debug mode is enabled.
- Snapshot capture remains available when submit confirmation fails.
- Explicit deep-debug snapshot capture can be enabled with `CHATGPT_POST_SUBMIT_SNAPSHOT_MODE=deep`, `CHATGPT_DEEP_DEBUG=1`, or `CHATGPT_DOM_DIAGNOSTIC_MODE=deep`.
- Timing output includes:
  - `after_submit_snapshot_mode`
  - `after_submit_snapshot_skipped_reason`
  - `after_submit_composer_snapshot_seconds`
  - `submit_accounted_seconds`
  - `submit_unaccounted_seconds`

## Validation performed

- Python compile check for `promptbranch_browser_auth/client.py`.
- Focused pytest covering successful button-submit snapshot skipping, version output, container health version, and compose tag policy.
- ZIP verification and hygiene check.

## Slice / line confirmation

No slice or line was advanced. This is a repair-only release for old-chat successful-submit performance and timing-accounting preservation.
