# Release v0.1.47 — Read-only parallel task fan-out

## Baseline

Built from `chatgpt_claudecode_workflow-2_v0.1.46.zip`.

## Goal

Add a bounded read-only parallel task fan-out surface while preserving the scheduler policy that writes to the same conversation serialize through an exclusive task lock.

## Changes

- Added `promptbranch_task_fanout.py` with read-only fan-out policy, target parsing, plan payloads, and result payloads.
- Added `pb parallel policy --json`.
- Added `pb parallel task show ... --json`.
- Added `pb parallel task show ... --plan-only --json`.
- Added parser, CLI, and module tests for fan-out planning and execution.
- Added `task_fanout` operation classification to the parallel architecture registry.

## Boundaries

This release is read-only. It does not add parallel `pb ask`, source mutation routing, artifact adoption, or release lifecycle execution.

Same-conversation writes remain serialized by policy:

```text
task:{conversation_id}:exclusive
```

## Lightweight validation

Recommended slice validation:

```bash
python3 -m pytest -q \
  tests/test_promptbranch_parallel.py \
  tests/test_promptbranch_profile_registry.py \
  tests/test_promptbranch_scheduler.py \
  tests/test_promptbranch_backend_reads.py \
  tests/test_promptbranch_task_fanout.py \
  tests/test_cli_parser.py::test_parser_accepts_parallel_task_show_command \
  tests/test_promptbranch_cli.py::test_parallel_task_show_plan_only_emits_read_only_policy \
  tests/test_promptbranch_cli.py::test_parallel_task_show_fetches_targets_without_mutating_current_state

python3 -m compileall -q .

pb parallel policy --json | python3 -m json.tool
pb parallel task show --task 1 --plan-only --json | python3 -m json.tool
pb test artifact-roundtrip --json --path . | python3 -m json.tool
```
