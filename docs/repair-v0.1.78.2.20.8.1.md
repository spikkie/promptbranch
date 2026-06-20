# Repair v0.1.78.2.20.8.1 — release ZIP root control-file packaging repair

## Scope

This is a packaging-only repair for `v0.1.78.2.20.8`.

## Base release

- Base candidate: `chatgpt_claudecode_workflow-2_v0.1.78.2.20.8.zip`
- Repair candidate: `chatgpt_claudecode_workflow-2_v0.1.78.2.20.8.1.zip`

## Reason

The `v0.1.78.2.20.8` transported ZIP failed release import planning because the archive omitted the required repo-root `.gitignore` file. The repository worktree contained `.gitignore`; the defect was in the packaged ZIP surface, not in the source tree implementation.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `tests/test_promptbranch_version.py`
- `docs/repair-v0.1.78.2.20.8.1.md`
- `docs/project/status.md`
- `docs/project/release-status.md`
- `docs/project/decisions.md`
- `docs/project/migration.md`

The repair ZIP also intentionally includes the repo-root `.gitignore` entry.

## Validation performed

- Python compile check for version and touched runtime modules.
- Focused version/control-surface tests.
- ZIP integrity check.
- ZIP hygiene check.
- Required root-file check including `.gitignore` and `.not_to_zip`.

## Slice/line movement

No normal slice advanced. This repair only fixes the packaging defect in the intended `v0.1.78.2.20.8` repair candidate.
