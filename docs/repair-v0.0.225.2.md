# Repair release v0.0.225.2

## Base release

`v0.0.225`

## Repair version

`v0.0.225.2`

## Reason

`v0.0.225.1` made `scripts/post-release-validation.sh` fail when the installed runtime version differed from the adopted artifact/source baseline. That was too strict for post-release validation: an unadopted candidate should be reported as pending adoption, not as a failed validation gate. Adoption must be explicit through `--adopt-if-accepted`.

## Files changed

- `scripts/post-release-validation.sh`
- `tests/test_post_release_validation.py`
- `docs/repair-v0.0.225.2.md`

## Validation performed

- `bash -n scripts/post-release-validation.sh`
- focused post-release validation semantic tests
- version-surface focused tests
- ZIP CRC / no-wrapper / hygiene verification

## Scope confirmation

No MVP slice or line was advanced. No ask/reply protocol, artifact-intake, candidate-test, source-sync, Project Source upload, adoption model, or MCP policy behavior was changed beyond the post-release validation helper.
