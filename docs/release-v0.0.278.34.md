# Release v0.0.278.34

## Scope

Repair the ask response-wait budget contract after the v0.0.278.33 stale-guard run still surfaced `service_client_read_timeout` instead of a structured `submit_confirmed_answer_timeout` result.

## Changes

- Propagate the CLI/service client timeout budget into `/v1/ask` as `service_timeout_seconds`.
- Create one absolute ask-operation deadline at browser-operation start.
- Reserve cleanup/trace time before the outer client timeout.
- Cap backend-first JSON response waiting by the absolute ask deadline.
- Expose deadline/budget evidence in response wait and phase timing fields.
- Preserve submit confirmation and stale-answer gates; no answer is accepted without fresh-marker verification.

## Validation intent

A confirmed submit that does not produce a fresh parseable answer must return structured `submit_confirmed_answer_timeout` before the CLI client reaches its read timeout.
