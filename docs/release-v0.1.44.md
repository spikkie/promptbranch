# Release v0.1.44 — service-profile bounded wait queue

## Base

Built from accepted/working repair baseline `chatgpt_claudecode_workflow-2_v0.1.43.1.zip`.

## Goal

Start the planned `v0.1.44` parallel-architecture slice by routing service-backed Project Source uploads through a bounded wait on the shared browser profile instead of using the short fail-fast contention path.

## Changes

- `pb src add` and `project-source-add` now use the service-profile bounded wait queue by default.
- Default source-add service profile wait is `600` seconds.
- Added `--no-queue` to opt out and use the service default short contention behavior.
- `pb browser status --json` now reports service queue policy metadata.
- Added scheduler helper `service_browser_queue_policy()`.
- Added focused tests for default queue wait, opt-out behavior, browser status queue metadata, and scheduler policy.

## Boundary

This release does **not** implement service profile cloning or broad parallel service execution. It serializes through the existing single service profile and waits safely before failing.

## Lightweight tests

```bash
python3 -m pytest -q \
  tests/test_promptbranch_parallel.py \
  tests/test_promptbranch_profile_registry.py \
  tests/test_promptbranch_scheduler.py \
  tests/test_cli_parser.py::test_parser_accepts_debug_parallel_plan_command \
  tests/test_cli_parser.py::test_parser_accepts_profile_registry_commands \
  tests/test_cli_parser.py::test_parser_accepts_queue_inspection_commands \
  tests/test_cli_parser.py::test_parser_accepts_browser_status_and_source_add_profile_wait \
  tests/test_promptbranch_cli.py::test_debug_parallel_plan_emits_command_metadata_json \
  tests/test_promptbranch_cli.py::test_profile_list_command_emits_profile_registry_json \
  tests/test_promptbranch_cli.py::test_profile_pools_command_emits_flattened_pool_json \
  tests/test_promptbranch_cli.py::test_queue_status_command_emits_scheduler_json \
  tests/test_promptbranch_cli.py::test_queue_plan_command_emits_resource_plan_json \
  tests/test_promptbranch_cli.py::test_src_add_promotes_browser_profile_busy_to_top_level_payload \
  tests/test_promptbranch_cli.py::test_src_add_positional_file_delegates_as_file_source \
  tests/test_promptbranch_cli.py::test_src_add_no_queue_disables_service_profile_wait \
  tests/test_promptbranch_cli.py::test_browser_status_command_uses_service_client \
  tests/test_promptbranch_cli.py::test_browser_client_log_writes_to_stderr
```

```bash
python3 -m compileall -q .
pb --version
pb browser status --json | python3 -m json.tool
pb queue plan --operation src_add --context account_id=default --context project_id=demo --context service_id=default --json | python3 -m json.tool
pb test artifact-roundtrip --json --path . | python3 -m json.tool
```
