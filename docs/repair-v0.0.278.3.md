# Repair v0.0.278.3

## Base release

```text
chatgpt_claudecode_workflow_v0.0.278.2.zip
```

## Repair version

```text
v0.0.278.3
```

## Reason

`v0.0.278.2` correctly classified browser-profile lock contention, but live observation showed that `pb ask` could keep waiting after the ChatGPT UI had visibly returned to an idle composer state.

The specific observed UI signal was the composer voice button returning with the aria label/text `Use Voice`. That state means the answer generation surface is idle, but the ask completion observer did not treat it as a strong enough completion signal and could continue waiting for additional expensive stability polls.

## Files changed

```text
promptbranch_browser_auth/client.py
tests/test_response_completion.py
VERSION
promptbranch_version.py
pyproject.toml
docker-compose.chatgpt-service.yml
promptbranch.egg-info/PKG-INFO
promptbranch.egg-info/SOURCES.txt
docs/repair-v0.0.278.3.md
```

## Changes

- Added explicit `Use Voice` selectors to the composer idle indicator set.
- Added idle composer label classification for labels such as `Use Voice`, `Start Voice`, and dictation variants.
- Added predicate-level ask/json wait logging fields:
  - `completion_ready`
  - `completion_blockers`
  - `strong_idle_completion`
  - `idle_label_visible`
  - `completion_reason`
- Added a strong idle completion path: when response content is present, the page is a conversation URL, stop/thinking indicators are absent, and an idle voice composer label is visible, the observer can complete without waiting for multiple additional expensive stability polls.
- Preserved the `browser_profile_busy` lock contention classification from `v0.0.278.2`.

## Validation performed

```text
python3 -m py_compile promptbranch_browser_auth/client.py
pytest -q tests/test_response_completion.py
```

Focused validation passed.

## Scope confirmation

This is a repair release only. It does not advance the normal release line, does not open a new slice, and does not implement the longer-term BrowserSessionManager + async job record architecture.
