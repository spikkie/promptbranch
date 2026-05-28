# Repair release v0.0.278.10

## Base release

v0.0.278.9

## Repair version

v0.0.278.10

## Reason

`v0.0.278.9` made submit timing mathematically reconcilable, but the fresh-task comparison showed that old task chats can make browser automation much slower. The observed failure mode was dominated by conversation DOM weight: large historical assistant/user turns and hundreds of code-block candidates caused broad selectors and post-submit composer snapshots to scale with old conversation history.

This repair adds DOM-weight diagnostics and narrows the successful fast path so response and composer probes prefer the latest assistant turn / primary composer controls before falling back to broad historical selectors.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `docker-compose.chatgpt-service.yml`
- `promptbranch_browser_auth/client.py`
- `tests/test_project_list_browser_client.py`
- `docs/repair-v0.0.278.10.md`

## Changes

- Added conversation DOM-weight diagnostics to ask timings:
  - `conversation_assistant_turn_count`
  - `conversation_user_turn_count`
  - `conversation_generic_turn_count`
  - `conversation_code_block_count`
  - `large_conversation_dom_detected`
  - `recommend_new_task_when_large`
  - `dom_weight_capture_seconds`
- Added a minimal post-submit composer snapshot path:
  - avoids broad `div[contenteditable]` fallback scans after successful submit dispatch
  - records `after_submit_snapshot_mode=post_submit_minimal`
  - preserves the v0.0.278.9 `submit_accounted_seconds` / `submit_unaccounted_seconds` reconciliation invariant
- Changed assistant text extraction to prefer the latest assistant turn and avoid historical `evaluate_all` over all matching turns.
- Changed JSON response extraction to inspect code blocks scoped to the latest assistant turn before using global historical JSON/code selectors.
- Added focused regression tests for latest-turn/limited historical selector behavior.

## Validation performed

- `python3 -m py_compile promptbranch_browser_auth/client.py`
- Focused pytest:
  - `tests/test_project_list_browser_client.py::test_submit_prompt_button_path_skips_slow_user_turn_dom_wait_after_running_confirmation`
  - `tests/test_project_list_browser_client.py::test_extract_last_text_from_selector_avoids_full_historical_evaluate_all`
  - `tests/test_project_list_browser_client.py::test_try_extract_json_payload_prefers_latest_assistant_turn_scope`
- Broader focused pytest set before packaging.
- ZIP reopened and verified after packaging:
  - no wrapper folder
  - `VERSION` is `v0.0.278.10`
  - no cache/temp/log/nested ZIP hygiene violations

## Scope confirmation

This is a repair release only. No slice or line was advanced. No release workflow redesign, scheduler redesign, source-add behavior change, or artifact/adoption policy change was introduced.
