# Repair release v0.0.225.1

## Base release

`chatgpt_claudecode_workflow_v0.0.225.zip`

## Repair version

`v0.0.225.1`

## Reason

`v0.0.225` introduced the migrated-candidate test gate, but the post-release validation helper treated `pb artifact current --json` exit code success as sufficient. That missed semantic baseline drift where the installed runtime was `v0.0.225` while the adopted artifact/source baseline still pointed to an older release.

## Files changed

- `scripts/post-release-validation.sh`
- `tests/test_post_release_validation.py`
- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- version-surface tests and service image metadata
- `README.md`
- `docs/repair-v0.0.225.1.md`

## Validation performed

- `bash -n scripts/post-release-validation.sh`
- focused pytest for post-release validation semantic checks
- version-surface tests
- Python compile checks
- ZIP CRC and hygiene checks

## Scope confirmation

No MVP slice or line was advanced. This repair only adds semantic baseline-version checking to post-release validation and updates version metadata to the repair version.

No protocol schema, artifact intake, candidate migration, candidate testing, source upload, Project Source mutation, or adoption behavior was changed.
