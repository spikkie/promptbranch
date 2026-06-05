# Release v0.1.43.1 — scheduler packaging repair

## Repair metadata

- Base release: `v0.1.43`
- Repair version: `v0.1.43.1`
- Release type: repair
- Slice/line advancement: none

## Reason

`v0.1.43` installed successfully, but the installed `promptbranch` console entry point failed before command dispatch:

```text
ModuleNotFoundError: No module named 'promptbranch_scheduler'
```

The source tree contained `promptbranch_scheduler.py`, and source-tree focused tests passed, but `pyproject.toml` did not list the new top-level module in `tool.setuptools.py-modules`. The installed distribution therefore omitted it.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `docker-compose.chatgpt-service.yml`
- `tests/test_promptbranch_scheduler.py`
- `docs/release-v0.1.43.1.md`

## Validation performed

```bash
python3 -m compileall -q .

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

python3 -m venv /tmp/pb-0143-1-install-smoke
/tmp/pb-0143-1-install-smoke/bin/python -m pip install <zip>
/tmp/pb-0143-1-install-smoke/bin/pb queue status --json | python3 -m json.tool
/tmp/pb-0143-1-install-smoke/bin/pb queue plan --operation src_add --context account_id=default --context project_id=demo --context service_id=default --json | python3 -m json.tool
```

## Explicit no-advance confirmation

This repair does not advance the parallel architecture slice plan. It only fixes packaging metadata and adds a regression test to ensure `promptbranch_scheduler.py` is included in installed distributions.
