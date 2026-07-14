# Repair v0.1.103.10.100

## Baseline

- Accepted/current: `v0.1.103.10.68`
- Input diagnostic candidate: `v0.1.103.10.99`
- Repair mode: diagnostic-only; no normal scope advancement

## Problem

The live `v0.1.103.10.99` diagnostic completed Project Source processing but later stopped making progress while the service remained healthy. Generic Fetch/XHR trace settlement performed unbounded response-capture waits, including unbounded `response.text()` calls.

## Repair

- Bound generic trace settlement to a short explicit timeout.
- Bound non-streaming response body reads.
- Never read `text/event-stream`, NDJSON, JSON-sequence, multipart-stream, or `process_upload_stream` bodies through the generic trace.
- Cancel unresolved capture tasks and safely detach tasks that do not acknowledge cancellation.
- Report completed, failed, cancelled, pending and detached task counts.
- Report unresolved task URL, phase, method, resource type and content type using sanitized values.
- Preserve completed trace events.
- Return `fetch_xhr_protocol_watch_settle_timeout` as structured diagnostic JSON.

## Preserved behavior

- `v0.1.103.10.99` Project Source processing-stream handling remains unchanged.
- `v0.1.103.10.96` deletion and Recently deleted handling remains unchanged.
- Normal `pbsa` remains unchanged.
- No canonical release `pbsa` or adoption is performed.
