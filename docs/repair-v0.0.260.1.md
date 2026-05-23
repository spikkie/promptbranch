# Repair release v0.0.260.1

## Base release

v0.0.260 (`chatgpt_claudecode_workflow_v0.0.260.zip`)

## Repair version

v0.0.260.1 (`chatgpt_claudecode_workflow_v0.0.260.1.zip`)

## Reason

The v0.0.260 strict final Artifact Intake MVP validation adopted the release and verified current baseline consistency, but then ran a post-adoption protocol smoke that intentionally produced a `no_artifact` reply. The subsequent `--require-real-candidate-mvp` candidate-run step resolved state from that latest no-artifact smoke reply and failed with `candidate_mvp_no_artifact_candidate`.

That was a validator sequencing/scope defect: post-adoption real-candidate completion must validate the release being finalized, not the latest no-artifact smoke reply.

## Files changed

- `VERSION`
- `promptbranch_version.py`
- `pyproject.toml`
- `promptbranch.egg-info/PKG-INFO`
- `promptbranch_cli.py`
- `scripts/post-release-validation.sh`
- `tests/test_post_release_validation.py`
- `docs/repair-v0.0.260.1.md`

## Validation performed

- `python3 -m compileall -q .`
- `bash -n scripts/post-release-validation.sh scripts/finalize-artifact-intake-mvp.sh`
- Focused parser/runtime/version tests passed.
- Focused candidate-run repair smoke passed: `--require-real-candidate --require-complete --version v0.0.260.1` accepts a scoped already-adopted current baseline without resolving the latest no-artifact protocol reply.
- Focused release-doctor version tests passed.
- Extracted ZIP smoke passed: `promptbranch 0.0.260.1`, Python compile, shell syntax, and candidate-run help.

## Scope confirmation

No slice, line, planned scope, Project Source state, Git state, or adoption state was advanced by this repair. The repair only corrects the intended v0.0.260 finalizer/validator behavior.
