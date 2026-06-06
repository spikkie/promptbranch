# Repair release v0.1.47.1 — Parallel architecture document consistency

## Base release

`chatgpt_claudecode_workflow-2_v0.1.47.zip`

## Repair version

`v0.1.47.1`

## Reason

`docs/design/promptbranch-parallel-execution-architecture.md` still had a stale status header from `v0.1.43` and a slice-plan table that duplicated `v0.1.46` while assigning read-only parallel task fan-out to the wrong release.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `docs/design/promptbranch-parallel-execution-architecture.md`
- `docs/release-v0.1.47.1.md`
- `tests/test_promptbranch_parallel_architecture_doc.py`

## Validation performed

Recommended repair validation:

```bash
python3 -m pytest -q tests/test_promptbranch_parallel_architecture_doc.py
python3 -m pytest -q tests/test_promptbranch_task_fanout.py tests/test_promptbranch_parallel_architecture_doc.py
python3 -m compileall -q .
pb parallel policy --json | python3 -m json.tool
pb parallel task show --task 1 --plan-only --json | python3 -m json.tool
pb test artifact-roundtrip --json --path . | python3 -m json.tool
```

## Scope confirmation

This repair does not advance the parallel execution line, does not open a new line, does not add protocol-bound parallel ask behavior, and does not widen any write path. `v0.1.48` remains the next normal release target for protocol-bound parallel ask planning.
