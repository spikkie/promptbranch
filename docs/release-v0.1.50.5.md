# Release v0.1.50.5

Repair release for `v0.1.50.4`.

## Base release

- Base artifact: `chatgpt_claudecode_workflow-2_v0.1.50.4.zip`
- Repair artifact: `chatgpt_claudecode_workflow-2_v0.1.50.5.zip`

## Reason

The `v0.1.50.4` full release-control run installed and started successfully, but the live browser test later failed because `remove_project_source` and temporary project cleanup saw `browser_profile_busy` while `add_project_source` still appeared to own the shared browser profile. Source-add persistence itself was verified with `verification_mode=post_refresh`, but the service lock lifecycle still needed stale-owner diagnostics and recovery.

## Scope

Narrow repair only. This release does not advance the Promptbranch feature line, source mutation scope, ask/reply protocol scope, or release lifecycle scope.

## Files changed

- `promptbranch_automation/service.py`
  - Add operation IDs for browser profile lock ownership.
  - Track active task, elapsed time, stale threshold, and public stale-lock diagnostics.
  - Clear active operations by operation ID to avoid clearing a newer owner.
  - Add stale active-operation recovery after bounded wait timeout.
  - Force-release only expired/stale in-process profile locks before retrying acquisition.
- `promptbranch_browser_auth/exceptions.py`
  - Extend `BrowserProfileBusyError` payload with active operation ID, elapsed time, stale threshold, expiry state, and recovery result.
- `promptbranch_container_api.py`
  - Add `PROMPTBRANCH_BROWSER_PROFILE_STALE_LOCK_SECONDS` / `CHATGPT_BROWSER_PROFILE_STALE_LOCK_SECONDS` setting support.
- `tests/test_promptbranch_automation_service.py`
  - Add stale add-project-source lock recovery regression coverage.
  - Add browser-status stale-lock diagnostics coverage.
- `VERSION`, `pyproject.toml`, `promptbranch_version.py`, `docker-compose.chatgpt-service.yml`, `tests/test_compose_timeout_policy.py`
  - Refresh version metadata to `v0.1.50.5` / `0.1.50.5`.

## Validation performed

- `python3 -m py_compile promptbranch_automation/service.py promptbranch_browser_auth/exceptions.py promptbranch_container_api.py`
- `pytest -q tests/test_promptbranch_automation_service.py`
- `python3 -m compileall -q .`
- focused release/version tests before packaging
- ZIP hygiene and root-layout inspection after packaging

## Line/slice confirmation

No slice, line, or planned product scope was advanced. This is a repair-only release for browser-profile lock finalization/stale-lock handling in the intended `v0.1.50` repair line.
