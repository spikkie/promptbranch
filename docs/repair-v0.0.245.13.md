# Repair v0.0.245.13

Base release: `v0.0.245.12`
Repair version: `v0.0.245.13`

## Reason

`v0.0.245.12` fixed no-artifact artifact-intake dry-run validation, but the finalizer still failed during the post-adoption protocol smoke when the CLI HTTP client timed out waiting for `/v1/ask` even though protocol/debug records were created and the browser/service side may have completed the request.

## Scope

This repair is limited to protocol-smoke recovery after a service-client read timeout.

No normal release scope was advanced.

## Files changed

- `promptbranch_cli.py`
- `tests/test_promptbranch_cli.py`
- version metadata files

## Behavior change

When `pb ask --protocol --parse-reply` hits a service-client read timeout, Promptbranch now:

1. Attempts to recover from a persisted validated protocol-run record for the same request.
2. If no record is available, re-reads the selected task transcript and validates the reply for the same request.
3. Returns `status=recovered_after_service_timeout` only when the recovered reply validates against the original request.
4. Keeps failure closed when no matching valid reply exists.
5. Allows artifact intake to treat `recovered_after_service_timeout` as a validated protocol run.

## Validation performed

- `py_compile` passed.
- Focused protocol timeout recovery tests passed.
- Focused artifact-intake recovered-run tests passed.

## Slice state

No slice, MVP phase, or release line was advanced. This is a repair-only release.
