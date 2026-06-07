# Release v0.1.50.2

Repair release for `v0.1.50.1`.

## Base release

`chatgpt_claudecode_workflow-2_v0.1.50.1.zip`

## Repair reason

The `v0.1.50.1` reconciliation repair ZIP omitted the repository-root `.gitignore` file. The release-control import doctor requires root control files, including `.gitignore`, `.not_to_zip`, `VERSION`, `pyproject.toml`, and the release-control script. Missing `.gitignore` is a ZIP packaging defect because extracted candidates no longer carry the repository ignore policy needed to protect local/generated files during follow-up install, adoption, and Git safety checks.

## Files changed

- `.gitignore`
- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `docs/release-v0.1.50.2.md`

## Validation performed

- Verified `.gitignore` exists at ZIP root.
- Verified required root files exist in the candidate ZIP.
- `python3 -m compileall -q .`
- focused release lifecycle scheduler and reconciliation tests
- `pb release reconcile-current --json` strict JSON smoke
- `pb release lifecycle --dry-run --json` strict JSON smoke
- `pb test artifact-roundtrip --json --path .`
- ZIP root and hygiene inspection

## Scope control

No slice or line was advanced. This repair does not add live lifecycle phase routing, source mutation execution, artifact adoption execution, policy sync execution, or Git mutation. It only restores the required repository-root `.gitignore` file omitted from `v0.1.50.1` and bumps the repair version.
