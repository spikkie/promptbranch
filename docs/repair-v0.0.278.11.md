# Repair release v0.0.278.11

Base release: v0.0.278.10
Repair version: v0.0.278.11

## Reason

v0.0.278.10 correctly exposed old-task DOM weight, but its default diagnostics still performed expensive full-history counts in large chats. Old task evidence showed hundreds of conversation turns and more than a thousand code blocks, with DOM-weight capture itself taking tens of seconds.

## Scope

This repair keeps the v0.0.278.10 latest-turn response direction but makes DOM diagnostics cheap/capped by default. Full historical DOM/code-block scans are reserved for explicit deep diagnostic mode or fallback/failure paths.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `docker-compose.chatgpt-service.yml`
- `promptbranch_browser_auth/config.py`
- `promptbranch_automation/automation.py`
- `promptbranch_browser_auth/client.py`
- `tests/test_project_list_browser_client.py`
- `docs/repair-v0.0.278.11.md`

## Behavior

- Default DOM diagnostic mode is `light`.
- `CHATGPT_DOM_DIAGNOSTIC_MODE=deep` restores exact historical counts.
- `CHATGPT_DOM_DIAGNOSTIC_MODE=disabled` skips DOM-weight diagnostics.
- Light mode counts only primary assistant/user/generic selectors and skips full historical code-block counting.
- Response JSON extraction tries latest-turn scoped code first, then latest-turn text, and only then historical JSON fallback.
- Timing output includes:
  - `dom_weight_capture_mode`
  - `dom_weight_diagnostic_mode`
  - `dom_weight_capture_capped`
  - `dom_weight_capture_skipped_reason`
  - `historical_scan_used`
  - `historical_scan_seconds`
  - `response_extraction_mode`
  - `response_historical_scan_used`
  - `response_historical_scan_seconds`

## Validation performed

- Python compile check over repository Python files.
- Focused pytest covering version, submit timing, DOM diagnostic modes, and latest-turn JSON extraction ordering.
- ZIP verification and hygiene check.

## Slice / line confirmation

No slice or line was advanced. This is a repair-only release for successful-path DOM diagnostic cost and extraction ordering.
