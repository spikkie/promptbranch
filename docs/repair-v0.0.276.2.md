# Repair v0.0.276.2

## Base release

`chatgpt_claudecode_workflow_v0.0.276.1.zip`

## Repair version

`v0.0.276.2`

## Reason

Operators needed a manual, repo-local explanation of what `scripts/finalize-artifact-intake-mvp.sh` actually does and how to validate it without treating the wrapper as a black box.

The script itself was already intentionally thin, but its operational behavior was easy to misunderstand because the real lifecycle work is delegated to `scripts/post-release-validation.sh` with forced finalization flags.

## Files changed

- `docs/howto/15-finalize-artifact-intake-mvp.md`
- `docs/howto/README.md`
- `docs/mvp-definition-of-done.md`
- version metadata surfaces (`VERSION`, `pyproject.toml`, `promptbranch_version.py`, `promptbranch.egg-info/PKG-INFO`)
- version-current tests
- `promptbranch.egg-info/SOURCES.txt`
- `docs/repair-v0.0.276.2.md`

## Repair behavior

No runtime behavior changed.

The new manual documents:

- the wrapper/delegation contract
- the forced `--adopt-if-accepted --complete-candidate-mvp` semantics
- accepted, rejected, and conflicting flags
- delegated post-release validation phases
- manual preflight checks
- wrapper-contract tests using a fake delegated script
- manual end-to-end finalization steps
- release-log evidence files
- summary interpretation
- failure triage

## Validation performed

- Shell syntax check for `scripts/finalize-artifact-intake-mvp.sh` and `scripts/post-release-validation.sh`.
- Focused wrapper-contract pytest coverage for finalizer delegation and conflicting flag rejection.
- Python compile check for project Python files.
- ZIP layout and hygiene verification after packaging.

## Scope confirmation

No slice or line was advanced. This repair does not change candidate intake, download, verification, migration, candidate-test, adoption, Project Source mutation, MCP behavior, skill behavior, release planning, or browser automation behavior. It only documents the final Artifact Intake MVP finalizer and updates version metadata for the repair artifact.
