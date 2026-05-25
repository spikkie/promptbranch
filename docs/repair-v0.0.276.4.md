# Repair v0.0.276.4

## Base release

`chatgpt_claudecode_workflow_v0.0.276.3.zip`

## Repair version

`v0.0.276.4`

## Reason

A strict final Artifact Intake MVP run with `--require-real-candidate-mvp` could still pass candidate MVP completion when `pb artifact candidate-run` reported an already-adopted current baseline as the proof source. That proves current/adoption state, but it does not prove the ZIP download path. The observed evidence was:

```json
"download_performed": false
```

For the MVP claim, strict real-candidate validation must fail unless candidate-run proves a real artifact download.

## Files changed

- `scripts/post-release-validation.sh`
- `scripts/finalize-artifact-intake-mvp.sh`
- `docs/howto/15-finalize-artifact-intake-mvp.md`
- `docs/howto/16-manual-pb-command-use-cases.md`
- `tests/test_post_release_validation.py`
- version metadata surfaces (`VERSION`, `pyproject.toml`, `promptbranch_version.py`, `promptbranch.egg-info/PKG-INFO`)
- version-current tests
- `promptbranch.egg-info/SOURCES.txt`
- `docs/repair-v0.0.276.4.md`

## Repair behavior

When `--complete-candidate-mvp` and `--require-real-candidate-mvp` are both active, `scripts/post-release-validation.sh` now inspects the candidate-run JSON after a successful candidate-run command and requires:

```json
"mvp_complete": true,
"mvp_completion.status": "candidate_mvp_complete",
"download_performed": true
```

If the proof is only `adopted_current` and `download_performed=false`, the post-release validation fails and classifies the defect as:

```text
artifact_download_proof_failure
```

The finalizer forwards `--require-real-candidate-mvp`, so `scripts/finalize-artifact-intake-mvp.sh --require-real-candidate-mvp` now fails closed when the ZIP download path is not proven.

## Validation performed

- Shell syntax check for `scripts/finalize-artifact-intake-mvp.sh`, `scripts/post-release-validation.sh`, and `chatgpt_claudecode_workflow_release_control.sh`.
- Python compile check for project Python files.
- Parser/version smoke checks.
- Targeted fake candidate-run evidence check showed `artifact_download_proof_failure` is produced when `download_performed=false` and proof source is `adopted_current`.
- ZIP layout and hygiene verification after packaging.

## Scope confirmation

No slice or line was advanced. This repair changes only the finalizer/post-release validation gate for strict real-candidate MVP proof. It does not change artifact download implementation, candidate download mechanics, migration mechanics, adoption mechanics, Project Source mutation behavior, MCP behavior, skill behavior, release planning, or browser automation behavior.
