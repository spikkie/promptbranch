# Repair v0.0.278.8 — Submit Timing Decomposition and Send-Button Readiness

## Base release

v0.0.278.7

## Repair version

v0.0.278.8

## Reason

Live v0.0.278.7 validation proved that submit confirmation no longer depends on slow user-turn DOM evidence, but the ask path could still spend several minutes in a broad `submit_wait_seconds` phase when the send button was reported unavailable and Enter fallback was used.

The remaining defect was twofold:

1. `submit_wait_seconds` was too broad for diagnosis and could hide expensive pre-submit DOM scans.
2. The send-button path probed only the first matching element for each selector, which could miss a later visible/enabled send button and fall back to Enter unnecessarily.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `promptbranch_browser_auth/client.py`
- `docs/repair-v0.0.278.8.md`

## Changes

- Split submit timing into smaller fields:
  - `composer_state_capture_seconds`
  - `user_turn_state_capture_seconds`
  - `assistant_turn_count_seconds`
  - `send_button_probe_seconds`
  - `send_button_wait_seconds`
  - `send_button_click_seconds`
  - `send_button_retry_used`
  - `send_button_retry_reason`
  - `send_button_retry_seconds`
  - `enter_fallback_decision_seconds`
  - `enter_fallback_press_seconds`
  - `submit_confirmation_seconds`
  - `submit_total_seconds`
- Changed `submit_wait_seconds` to use the bounded interactive submit phase reported by `_submit_prompt`, not broad pre-submit capture time.
- Avoided full pre-submit user-turn DOM scans in `_submit_prompt`; submit confirmation already uses running-state, assistant-turn, and conversation-URL signals.
- Repaired send-button readiness by probing up to five matching controls per selector instead of only `.first`.
- Added a post-focus send-button retry before Enter fallback when the prompt text is present but no enabled send button was found during the bounded wait.
- Preserved v0.0.278.7 submit-confirmation behavior and v0.0.278.4 browser profile lock behavior.

## Validation performed

- Python compilation for repository Python files.
- Focused pytest coverage for parser/container/service-client/automation/CLI behavior.
- ZIP hygiene verification during packaging.

## Slice/line advancement

No slice or line was advanced. This is a repair-only release for the intended v0.0.278.x ask latency line.
