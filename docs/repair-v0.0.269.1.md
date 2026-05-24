# Repair v0.0.269.1

## Base release

`chatgpt_claudecode_workflow_v0.0.269.zip`

## Repair version

`v0.0.269.1`

## Reason

The accepted `v0.0.269` source-overwrite path could delete collateral Project Source rows during remembered file-source overwrite removal. The observed failure removed `architecture-process_0.12.0.zip` while the operator attempted to overwrite `ib_forex_trading.0.231.6.2.zip`.

## Files changed

- `promptbranch_automation/service.py`
- `promptbranch_browser_auth/client.py`
- `chatgpt_browser_auth/client.py`
- `tests/test_promptbranch_automation_service.py`
- `tests/test_project_resolve.py`
- version metadata surfaces (`VERSION`, `pyproject.toml`, `promptbranch_version.py`, `docker-compose.chatgpt-service.yml`, `promptbranch.egg-info/PKG-INFO`)
- `docs/repair-v0.0.269.1.md`

## Repair behavior

Remembered file-source overwrite removal now derives a clean exact file-source name from the basename, display name, requested match, or remembered candidates instead of reusing the full card identity such as `File contents may not be accessible`.

The remembered overwrite path now calls source remove with `exact=True`. Exact source-remove lookup no longer falls back to broad/global action-button discovery when it cannot find a scoped action control for the exact matched source card.

This prevents a stale or generic remembered source identity from driving a destructive click against a neighboring Project Source row.

## Validation performed

- `py_compile` for changed runtime/test files.
- Focused service tests for remembered overwrite classification and fail-closed handling.
- Focused source-remove tests for exact scoped action lookup and collateral detection.
- ZIP layout and hygiene verification after packaging.

## Scope confirmation

No slice or line was advanced. This repair does not change protocol schema, artifact intake semantics, release lifecycle state, normal release planning, source-add persistence timing, or Project Source add behavior outside source-remove collateral prevention.
