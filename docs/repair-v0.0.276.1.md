# Repair v0.0.276.1

## Base release

`chatgpt_claudecode_workflow_v0.0.276.zip`

## Repair version

`v0.0.276.1`

## Reason

The `v0.0.276` `pb artifact candidate-next --json` top-level selector correctly stopped selecting stale accepted historical candidates, but the nested per-candidate inventory row could still expose a stale `repair_or_remigrate_candidate` recommendation for an already accepted candidate whose ZIP had been pruned.

That nested recommendation was operationally overridden by the safe top-level `no_actionable_candidate` result, but it was still misleading for tools that inspect `inventory.candidates[].recommended_next_command` directly.

## Files changed

- `promptbranch_cli.py`
- `tests/test_promptbranch_cli.py`
- version metadata surfaces (`VERSION`, `pyproject.toml`, `promptbranch_version.py`, `promptbranch.egg-info/PKG-INFO`)
- `docs/repair-v0.0.276.1.md`

## Repair behavior

Candidate lifecycle recommendation now checks `candidate_accepted` before ZIP-existence and verification repair checks. Historical accepted candidate rows therefore report `candidate_already_accepted` and point to `pb artifact current --json` instead of suggesting artifact intake/remigration.

The top-level `candidate-next` behavior from `v0.0.276` remains unchanged: stale accepted candidates are still reported in inventory but are not selected as actionable next candidates.

## Validation performed

- Python compile check for the repository.
- Focused regression test for stale accepted missing-ZIP candidate filtering and nested inventory recommendation behavior.
- ZIP layout and hygiene verification after packaging.

## Scope confirmation

No slice or line was advanced. This repair does not change candidate intake, download, verification, migration, candidate-test, adoption, Project Source mutation, MCP behavior, skill behavior, or release planning. It only corrects stale nested recommendation reporting for already accepted historical candidates.
