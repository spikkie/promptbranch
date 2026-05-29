# Release v0.0.278.48

## Scope

Repair the submit-causality classifier while preserving the v0.0.278.46 retry behavior.

## Baseline

Built from `chatgpt_claudecode_workflow_v0.0.278.46.zip`.

## Problem

`v0.0.278.47` exposed that a marker-bearing `/backend-api/f/conversation/prepare` request could be promoted as `network_submit_request`. That skipped the known-good retry path and led to `ok=false`/timeout.

## Change

- `/backend-api/f/conversation/prepare` remains diagnostic prepare traffic.
- Prepare requests are never accepted as `network_submit_request` confirmation, even when they carry the current marker.
- Only marker-bearing final message-submit network requests can satisfy `network_submit_request` causality.
- Existing raw Enter primary, prepare-only fast-fail, trusted-refill retry, and fast latest-answer promotion behavior from v0.0.278.46 is retained.

## Validation

- `python3 -m compileall -q .`
- focused browser-client submit causality tests
- clean extracted ZIP hygiene verification
