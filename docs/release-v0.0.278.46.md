# Release v0.0.278.46

Diagnostic-only continuation from `chatgpt_claudecode_workflow_v0.0.278.42.zip`.

## Intent

Do not change submit behavior or speed policy.  Preserve the last known-good `.42` path and add observational evidence to explain why the `.42` retry path succeeds while later speed attempts failed.

## Changes

- Added lightweight submit-readiness diagnostics around the primary raw-Enter dispatch and the trusted-refill retry dispatch.
- Added passive keyboard/input event probe collection for submit dispatch attempts.
- Added diagnostic snapshots for:
  - active element
  - composer selector and text/marker state
  - send button state
  - stop button state
  - document focus
  - active-within-composer relation
  - key/input/submit events observed during dispatch
- Kept `.42` behavior unchanged:
  - raw Enter primary
  - prepare-only fast-fail
  - trusted-refill + Enter retry
  - fast latest-turn answer promotion

## Non-goals

- No submit-order changes.
- No slim refill optimization.
- No new readiness gate.
- No acceptance of stale or prefix-only markers.

## Validation

- `python3 -m compileall -q .`
- Focused pytest suite covering browser client, CLI, service, container API, parser, and compose policy.
