# Repair release v0.0.278.6

## Base release

`chatgpt_claudecode_workflow_v0.0.278.5.zip`

## Repair version

`v0.0.278.6`

## Reason

`v0.0.278.5` fixed canonical answer rendering, but live asks still had poor operator latency visibility. The UI could appear complete while the CLI remained blocked, and the service did not expose enough phase timing to distinguish prompt-fill delay, submit-button wait, response wait, and return finalization. Browser status also showed stale `active_operation` metadata after the profile was available.

## Files changed

- `promptbranch_browser_auth/client.py`
  - Added ask phase timing instrumentation.
  - Added bounded prompt-fill fallback instrumentation.
  - Reduced submit-button wait before Enter fallback when no enabled button is found.
  - Added submit method and button-unavailable diagnostics.
- `promptbranch_automation/service.py`
  - Propagated browser profile lock wait timing into ask phase timings.
  - Cleaned browser status so stale lock-file metadata is exposed as last-operation metadata instead of active owner metadata.
- `promptbranch_container_api.py`
  - Exposed `ask_phase_timings` in the `/v1/ask` response model.
- Version metadata files and tests updated to `v0.0.278.6`.

## Validation performed

- Python compilation for repository Python files.
- Focused tests for browser status, ask JSON response metadata, CLI parser/rendering, service client, container API, timeout classification, and version consistency.
- ZIP hygiene verification after packaging.

## Scope confirmation

This repair did not advance a slice, open a new line, implement an async queue, or change the planned Promptbranch architecture. It only repairs ask-latency observability, submit fallback behavior, and stale browser-status metadata in the intended `v0.0.278.x` repair line.
