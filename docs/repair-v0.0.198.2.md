# Repair release v0.0.198.2

Base release: v0.0.198.1
Repair version: v0.0.198.2

## Reason

`v0.0.198.1` fixed repair-version parsing in release-control, but the full release path still failed when the configured legacy packager produced a git-hash ZIP such as `chatgpt_claudecode_workflow-f8f6bf5.zip` for a four-component repair version. The release-control script expected only canonical versioned ZIP names or `source_*` variants, so it could not find the generated artifact.

## Files changed

- `chatgpt_claudecode_workflow_release_control.sh`
- `tests/test_promptbranch_shell_scripts.py`
- `README.md`
- `UPGRADING.md`
- `docs/repair-v0.0.198.2.md`
- version metadata and version expectation tests updated from `v0.0.198.1` / `0.0.198.1` to `v0.0.198.2` / `0.0.198.2`

## Validation performed

- `bash -n chatgpt_claudecode_workflow_release_control.sh`
- focused shell-script regression tests
- Python compile checks
- ZIP CRC/testzip verification
- artifact hygiene verification

## Scope confirmation

No slice, line, planned feature scope, or project-source mutation behavior was advanced. This repair only fixes the intended `v0.0.198.x` release-control repair path.
