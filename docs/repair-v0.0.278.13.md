# Repair release v0.0.278.13

Base release: v0.0.278.12
Repair version: v0.0.278.13

## Reason

v0.0.278.12 correctly skipped post-submit composer snapshots on successful fast paths, but old-task service logs showed that `response_wait_seconds` still hid multiple response subphases. In particular, a parseable latest-turn JSON probe could occur before the logged payload stabilization event, and debug-artifact save time after stabilization was still reported inside `response_wait_seconds` while `completion_to_return_seconds` remained near zero.

This repair decomposes response wait timing and accounts for the post-stabilization return tail explicitly.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `docker-compose.chatgpt-service.yml`
- `promptbranch_browser_auth/client.py`
- `tests/test_project_list_browser_client.py`
- version assertion updates under `tests/`
- `docs/repair-v0.0.278.13.md`

## Implementation notes

- Adds response-wait timing breakdown fields for first probe, first JSON candidate, first parseable JSON, payload detection, payload stabilization, completion-signal probing, poll sleep, and post-stabilization return.
- Reclassifies the post-stabilization tail into `completion_to_return_seconds` so debug artifact writes and other after-completion work are not hidden inside `response_wait_seconds`.
- Preserves latest-turn JSON extraction, historical-scan avoidance, submit accounting, and `.12` post-submit snapshot skipping.

## Validation performed

- `python3 -m py_compile` over 106 Python files.
- Focused pytest:
  - `tests/test_project_list_browser_client.py`
  - `tests/test_chatgpt_container_api.py`
  - `tests/test_promptbranch_container_api.py`
  - `tests/test_compose_timeout_policy.py`
  - `tests/test_cli_parser.py::test_parser_accepts_version_subcommand`
  - `tests/test_promptbranch_cli.py::test_main_version_subcommand_outputs_release`
- Result: 68 passed.

## Scope confirmation

No slice or line was advanced. This repair only fixes diagnostic/accounting behavior for the intended v0.0.278.12 response-wait performance investigation.
