# Release v0.0.278.78

Repair release over v0.0.278.77.

## Reason

The visual artifact roundtrip prompt still allowed ChatGPT to return a partial Promptbranch reply envelope. Artifact intake correctly failed closed with `reply_schema_invalid`, but the prompt did not explicitly require the full ask/reply schema fields.

## Changes

- Hardened the shared ZIP artifact prompt builder used by release-candidate asks and visual artifact roundtrip tests.
- Required the reply envelope to include `schema`, `schema_version`, `summary`, and `next_step` in addition to the existing artifact fields.
- Required `schema` to be exactly `promptbranch.ask.reply` and `schema_version` to be exactly `1.0`.
- Added a focused regression test for the visual artifact roundtrip prompt schema contract.

## Validation

- `python3 -m compileall -q .`
- Focused prompt and visual artifact tests.
- Reopened packaged ZIP and verified layout/hygiene.

## Scope control

No artifact-intake relaxation was made. Invalid envelopes still fail closed.
