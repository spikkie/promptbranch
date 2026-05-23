# Release v0.0.256 — Real candidate artifact proof guard

## Scope

This release hardens the Artifact Intake MVP proof path so the real candidate
loop cannot be accidentally satisfied by a no-artifact protocol smoke reply.

## Changes

- Added `pb artifact candidate-run --require-real-candidate`.
- Added post-release validation forwarding via `--require-real-candidate-mvp`.
- Added finalizer wrapper forwarding for `--require-real-candidate-mvp`.
- Updated candidate-run JSON output with `require_real_candidate` and an explicit
  `candidate_run_real_candidate_required` failure state.
- Preserved the existing no-artifact normalization for ordinary post-release
  smoke validation unless the new real-candidate flag is explicitly used.

## Intended proof command

```bash
pb artifact candidate-run \
  --execute-until-blocked \
  --require-complete \
  --require-real-candidate \
  --json
```

For final MVP proof runs:

```bash
scripts/finalize-artifact-intake-mvp.sh \
  --version v0.0.256 \
  --target-version v0.0.257 \
  --require-real-candidate-mvp
```

## Safety boundary

- No Git commit by default.
- No Git push by default.
- No artifact acceptance without green candidate-test/adoption checks.
- No passing real-candidate proof when the latest protocol reply is `no_artifact`.

## Validation performed

- Python compile smoke for `promptbranch_cli.py`.
- Parser/candidate-run focused tests.
- Existing no-artifact post-release normalization path remains intact.

