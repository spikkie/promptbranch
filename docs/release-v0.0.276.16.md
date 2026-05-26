# Release v0.0.276.16

## Scope

Guarded candidate-run automation for the Artifact Intake MVP loop.

## Changes

- `pb artifact candidate-run` now accepts `--profile smoke|full` and forwards it to the delegated `candidate-test` command.
- `pb artifact candidate-run` now accepts `--accept-if-green` as the explicit gate for adoption.
- `candidate-run --execute-until-blocked` may automate download, verification, migration, and candidate-test, but stops at acceptance-ready unless `--accept-if-green` is supplied.
- Candidate-run JSON reports `test_profile` and `accept_if_green` so the operator can distinguish smoke-only proof from explicit adoption.

## Intended command

```bash
pb artifact candidate-run \
  --execute-until-blocked \
  --require-real-candidate \
  --profile smoke \
  --json
```

This should stop before adoption when the candidate is ready for acceptance.

Explicit adoption requires:

```bash
pb artifact candidate-run \
  --execute-until-blocked \
  --require-real-candidate \
  --profile smoke \
  --accept-if-green \
  --json
```

## Non-goals

- No automatic adoption by default.
- No full-suite default; full remains explicit with `--profile full`.
- No Project Source mutation.
