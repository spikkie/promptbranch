# Release v0.1.43 — scheduler/resource lock inspection slice

## Baseline

Built from `chatgpt_claudecode_workflow-2_v0.1.42.zip`.

## Goal

Start the planned scheduler/resource lock manager without changing live command execution yet.

This slice makes resource planning executable and testable before later slices route source mutations, service browser operations, or release lifecycle work through a queue.

## Changes

- Added `promptbranch_scheduler.py`.
- Added read-only scheduler commands:
  - `pb queue status --json`
  - `pb queue list --json`
  - `pb queue plan --operation ... --context key=value --json`
  - `pb queue conflicts --left-operation ... --right-operation ... --context key=value --json`
- Added focused scheduler tests in `tests/test_promptbranch_scheduler.py`.
- Added parser and CLI JSON tests for the queue commands.
- Updated `docs/design/promptbranch-parallel-execution-architecture.md`.
- Updated the cumulative parallel-line slice test plan.

## Boundary

This release is intentionally inspection-only.

It does **not**:

- route `pb src add` through a queue;
- clone service browser profiles;
- alter `pb ask` or `pb task` execution;
- mutate Project Sources;
- change artifact adoption or release lifecycle behavior.

## Lightweight tests for this slice

```bash
python3 -m pytest -q \
  tests/test_promptbranch_parallel.py \
  tests/test_promptbranch_profile_registry.py \
  tests/test_promptbranch_scheduler.py \
  tests/test_cli_parser.py::test_parser_accepts_debug_parallel_plan_command \
  tests/test_cli_parser.py::test_parser_accepts_profile_registry_commands \
  tests/test_cli_parser.py::test_parser_accepts_queue_inspection_commands \
  tests/test_promptbranch_cli.py::test_debug_parallel_plan_emits_command_metadata_json \
  tests/test_promptbranch_cli.py::test_profile_list_command_emits_profile_registry_json \
  tests/test_promptbranch_cli.py::test_profile_pools_command_emits_flattened_pool_json \
  tests/test_promptbranch_cli.py::test_queue_status_command_emits_scheduler_json \
  tests/test_promptbranch_cli.py::test_queue_plan_command_emits_resource_plan_json \
  tests/test_promptbranch_cli.py::test_browser_client_log_writes_to_stderr
```

```bash
python3 -m compileall -q .

pb debug parallel-plan --json | python3 -m json.tool
pb profile list --json | python3 -m json.tool
pb profile pools --json | python3 -m json.tool
pb queue status --json | python3 -m json.tool
pb queue plan --operation src_add \
  --context account_id=default \
  --context project_id=demo \
  --context service_id=default \
  --json | python3 -m json.tool
pb test artifact-roundtrip --json --path . | python3 -m json.tool
```

## Full-test policy

Full tests are deferred unless the operator wants to accept a major stable baseline or a later slice changes scheduler execution, service queue behavior, source mutations, artifact adoption, or release lifecycle behavior.
