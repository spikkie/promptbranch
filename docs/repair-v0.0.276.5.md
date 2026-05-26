# Repair v0.0.276.5

## Base release

`chatgpt_claudecode_workflow_v0.0.276.4.zip`

## Repair version

`v0.0.276.5`

## Reason

`v0.0.276.4` correctly failed strict final Artifact Intake MVP validation when `download_performed=false`, but the strict path still ran the default no-artifact protocol smoke:

```text
promptbranch ask "Protocol smoke only ... status no_artifact ... Do not create a ZIP."
```

That smoke can validate the reply-envelope contract, but it cannot prove ZIP candidate creation, download, or verification.

## Files changed

- `scripts/post-release-validation.sh`
- `docs/howto/15-finalize-artifact-intake-mvp.md`
- `docs/howto/16-manual-pb-command-use-cases.md`
- `docs/mvp-definition-of-done.md`
- `tests/test_post_release_validation.py`
- version metadata surfaces (`VERSION`, `pyproject.toml`, `promptbranch_version.py`, `promptbranch.egg-info/PKG-INFO`)
- version-current tests
- `promptbranch.egg-info/SOURCES.txt`
- `docs/repair-v0.0.276.5.md`

## Repair behavior

When `--require-real-candidate-mvp` is active, `scripts/post-release-validation.sh` now:

1. switches the protocol step from the no-artifact smoke to `pb ask-release`;
2. requests the expected target ZIP artifact for `--target-version`;
3. runs artifact intake with `--from-last-answer --download --verify`;
4. requires the artifact-intake evidence to contain `download_performed=true` and `verification_performed=true`;
5. allows candidate-run completion to rely on already-adopted current-baseline proof only when paired with the explicit artifact-intake download/verify proof.

Default non-strict behavior remains the existing no-artifact protocol smoke plus artifact-intake dry-run.

## Validation performed

- Shell syntax check for release/finalizer scripts.
- Parser/help smoke for `ask-release`, `artifact intake`, and release commands.
- Static pytest check proving the strict path contains `ask-release` plus artifact-intake `--download --verify` proof requirements.
- Python compile check for project Python files.
- ZIP layout and hygiene verification after packaging.

## Scope confirmation

No slice or line was advanced. This repair does not change Project Source mutation, artifact adoption, browser automation mechanics, release lifecycle adoption semantics, MCP behavior, or skill behavior. It only corrects the strict finalizer validation path so the real-candidate proof attempts artifact-producing `pb ask-release` and direct artifact-intake download/verify proof.
