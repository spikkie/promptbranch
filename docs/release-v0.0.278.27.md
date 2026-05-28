# Release v0.0.278.27 — Conduit token transport diagnostics

## Base artifact

```text
chatgpt_claudecode_workflow_v0.0.278.26.zip
```

## Target artifact

```text
chatgpt_claudecode_workflow_v0.0.278.27.zip
```

## Scope

This is a narrow diagnostic release. It preserves the fail-closed submit-causality guard from the previous releases and adds redacted tracing for the `conduit_token` returned by `/backend-api/f/conversation/prepare`.

## Changes

- Extracts prepare `conduit_token` only into private in-memory state.
- Emits only `sha256_12` fingerprints and booleans/counts in public evidence.
- Scans post-prepare request URL/body material for private token presence.
- Scans selected post-prepare response bodies for private token presence.
- Adds WebSocket frame sent/received diagnostics and private token scanning.
- Classifies conduit outcomes:
  - `submit_prepare_conduit_token_not_consumed`
  - `submit_conduit_transport_observed_without_commit`

## New evidence fields

```text
submit_prepare_conduit_token_present
submit_prepare_conduit_token_sha256_12
submit_conduit_transport_observed
submit_conduit_transport_kind
submit_conduit_token_seen_in_request
submit_conduit_token_seen_in_response
submit_conduit_token_seen_in_websocket
submit_conduit_websocket_frame_count
submit_conduit_error_hint
```

## Safety

Raw `conduit_token` values are not written to structured output, logs, release notes, or tests. Diagnostic evidence uses only hashes, booleans, counts, and transport-kind labels.

## Validation

```text
python3 -m py_compile promptbranch_browser_auth/client.py
focused conduit diagnostic tests
focused existing prepare/commit tests
```
