# Release v0.1.42 — named profile registry slice

## Base

Built from `chatgpt_claudecode_workflow-2_v0.1.41.1.zip`.

`v0.1.41.2` was not used as the baseline for this normal planned slice.

## Goal

Implement the planned `v0.1.42` slice from the parallel execution architecture: a read-only named profile registry for local browser profiles and future service profile queues.

## Changes

- Added `promptbranch_profiles.py`.
- Added `pb profile list --json`.
- Added `pb profile pools --json`.
- Added `pb profile pools --profile <name> --json`.
- Added `pb profile show <name> --json`.
- Added built-in `local-debug` profile metadata.
- Added built-in `service-default` profile metadata for `/app/.pb_profile`.
- Added optional JSON profile registry extension loading.
- Updated `pb debug parallel-plan --json` to include the lightweight cumulative test policy.
- Updated parallel architecture documentation with the named profile registry model.
- Added focused tests for the registry and CLI commands.

## Boundary

This slice is read-only metadata. It does not yet:

- change browser execution routing;
- clone service-side profiles;
- implement the scheduler;
- queue service-backed browser operations;
- make `pb src add` parallel-safe.

Those remain planned for later slices.

## Lightweight tests for this slice

```bash
python3 -m pytest -q \
  tests/test_promptbranch_parallel.py \
  tests/test_promptbranch_profile_registry.py \
  tests/test_cli_parser.py::test_parser_accepts_debug_parallel_plan_command \
  tests/test_cli_parser.py::test_parser_accepts_profile_registry_commands \
  tests/test_promptbranch_cli.py::test_debug_parallel_plan_emits_command_metadata_json \
  tests/test_promptbranch_cli.py::test_profile_list_command_emits_profile_registry_json \
  tests/test_promptbranch_cli.py::test_profile_pools_command_emits_flattened_pool_json \
  tests/test_promptbranch_cli.py::test_browser_client_log_writes_to_stderr
```

```bash
python3 -m compileall -q .
```

```bash
pb debug parallel-plan --json | python3 -m json.tool
pb profile list --json | python3 -m json.tool
pb profile pools --json | python3 -m json.tool
pb profile show service-default --json | python3 -m json.tool
pb test artifact-roundtrip --json --path . | python3 -m json.tool
```

## Full-test policy

Full tests are not required for every small architecture slice. Run full tests when a slice changes scheduler behavior, service browser queueing, Project Source mutation, artifact adoption, release lifecycle behavior, or when focused tests reveal an unexplained regression.
