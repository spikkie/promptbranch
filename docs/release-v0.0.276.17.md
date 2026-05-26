# Release v0.0.276.17

Repair release from v0.0.276.16.

## Scope

- Update `scripts/finalize-artifact-intake-mvp.sh` so it delegates directly to the native `pb artifact candidate-run` lifecycle command.
- Preserve `--require-real-candidate-mvp` as a strict proof mode.
- Fail unless candidate-run proves download, verification, migration, and candidate-test completion when real-candidate MVP proof is required.
- Keep adoption disabled by default; adoption is allowed only when `--accept-if-green` is passed explicitly.

## Non-goals

- No automatic adoption by default.
- No Project Source mutation changes.
- No change to the accepted candidate ZIP lifecycle semantics.
