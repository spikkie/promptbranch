# Release v0.1.45

Base release: v0.1.44.1
Release type: normal

## Scope

This slice starts the backend-first task/source read diagnostics work for the parallel execution architecture.

It adds a read-only diagnostic surface:

```bash
pb debug backend-reads --json
pb debug backend-reads --plan-only --json
pb debug backend-reads --operation task_list --json
pb debug backend-reads --operation source_list --json
```

## Changes

- Added `promptbranch_backend_reads.py`.
- Added backend-first read operation plans for task list and Project Source list.
- Added classifiers for task-list payloads using `source_counts`, `indexed_task_count`, and recent-state fallback metadata.
- Added classifier for Project Source list payloads that flags a `metadata_gap` when source-list payloads do not expose whether data came from backend/network or DOM fallback.
- Added `pb debug backend-reads` command.
- Added parser, CLI, module, and packaging tests.

## Boundary

This release is read-only. It does not change `pb task list`, `pb task show`, `pb src list`, `pb src add`, artifact adoption, or release lifecycle mutation behavior.

## Lightweight test plan

```bash
python3 -m pytest -q \
  tests/test_promptbranch_parallel.py \
  tests/test_promptbranch_profile_registry.py \
  tests/test_promptbranch_scheduler.py \
  tests/test_promptbranch_backend_reads.py \
  tests/test_cli_parser.py::test_parser_accepts_debug_backend_reads_command \
  tests/test_promptbranch_cli.py::test_debug_backend_reads_plan_only_emits_json \
  tests/test_promptbranch_cli.py::test_debug_backend_reads_collects_task_and_source_payloads

python3 -m compileall -q .

pb debug backend-reads --plan-only --json | python3 -m json.tool
pb debug backend-reads --operation task_list --plan-only --json | python3 -m json.tool
pb test artifact-roundtrip --json --path . | python3 -m json.tool
```

## Full-test trigger

Full tests are not required for this slice unless the diagnostic command exposes an unexplained runtime regression. Full tests are still required for scheduler/service queue behavior, source mutations, artifact adoption, release lifecycle changes, unexplained regressions, or major baseline acceptance.
