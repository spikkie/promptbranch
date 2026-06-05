# Release v0.1.41

## Scope

Start the Promptbranch parallel execution architecture line.

This release is the first slice only. It documents the architecture, adds command/resource classification metadata, exposes the plan through a read-only debug command, and fixes browser-client logging so `_log` diagnostics go to stderr instead of contaminating JSON stdout.

## Changes

- Added `docs/design/promptbranch-parallel-execution-architecture.md`.
- Added `promptbranch_parallel.py` with operation classification metadata and cumulative slice test plan.
- Added `pb debug parallel-plan --json`.
- Added `pb debug parallel-plan --operation <operation> --json`.
- Routed `promptbranch_browser_auth.client.ChatGPTBrowserClient._log()` output to stderr.
- Added regression tests for:
  - operation classification metadata;
  - parser support for `debug parallel-plan`;
  - JSON diagnostic output;
  - browser `_log` stderr behavior.

## Safety boundary

This release does not add a scheduler, queue, profile registry, backend-first read rewrite, parallel ask runner, source mutation queue, or release lifecycle locking yet.

It is intentionally read-only control-plane groundwork except for routing existing diagnostic logs from stdout to stderr.

## Validation

Run the slice tests:

```bash
python3 -m pytest -q \
  tests/test_promptbranch_parallel.py \
  tests/test_cli_parser.py::test_parser_accepts_debug_parallel_plan_command \
  tests/test_promptbranch_cli.py::test_debug_parallel_plan_emits_command_metadata_json \
  tests/test_promptbranch_cli.py::test_browser_client_log_writes_to_stderr
```

Compile check:

```bash
python3 -m compileall -q .
```

Command smoke:

```bash
pb debug parallel-plan --json | python3 -m json.tool
pb debug parallel-plan --operation src_add --json | python3 -m json.tool
```

## Next slice

`v0.1.42` should add the named profile registry so profile-pool tests no longer depend on the current working directory having `./.pb_profile_local_debug`.
