# chatgpt_claudecode_workflow v0.0.278.61

## Purpose

Build from v0.0.278.60 and prevent `pb ask` from typing into a composer that is still running or interrupted.

## Changes

- Added a pre-fill composer readiness gate before the main `pb ask` fill path.
- Requires `send-button` visible/enabled before fill.
- Rejects `stop-button`, thinking, and interrupted-answer states before prompt mutation.
- Returns `composer_not_ready_before_fill` instead of typing into a running composer.

## Validation

- `python3 -m py_compile promptbranch_browser_auth/client.py`
- focused pytest coverage for ready, stop-button, and interrupted-answer readiness states
