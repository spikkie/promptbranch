# Release v0.1.50.3

Repair release for `v0.1.50.2`.

## Base release

`chatgpt_claudecode_workflow-2_v0.1.50.2.zip`

## Repair reason

A live Project Sources upload showed `pb src add` returning `ok=true` and `persistence_verified=true` for a ZIP source while the service still exposed browser-profile contention on the next `pb src list`. The observed source-add save watcher had seen a commit request, but one relevant upload/commit request was still inflight. The browser client then accepted a pre-refresh DOM source-card match as persistence proof.

That is a mutation correctness defect: a transient source card or partially observed save request must not be treated as a committed Project Source. The source mutation contract requires settled/backend-confirmed state and a re-read verification before reporting persistence.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `promptbranch_browser_auth/client.py`
- `tests/test_project_source_capabilities.py`
- `tests/test_promptbranch_automation_service.py`
- `docs/release-v0.1.50.3.md`

## Behavior changed

- `pb src add` no longer treats `committed_with_stale_inflight_grace` as quiet when a relevant Project Source save request remains inflight.
- Source-add persistence verification now treats the current DOM card as provisional UI evidence only.
- `persistence_verified=true` now requires a refreshed Sources-surface verification.
- Successful source-add results expose verification evidence fields:
  - `verification_mode`
  - `ui_card_seen`
  - `post_refresh_verified`
  - `post_refresh_attempt`
  - `save_request_summary`
- Browser-status focused tests now assert the bounded profile wait queue metadata exposed by the current service implementation.

## Validation performed

- `python3 -m pytest tests/test_project_source_capabilities.py::test_verify_project_source_persistence_requires_refresh_after_current_surface_match tests/test_project_source_capabilities.py::test_verify_project_source_persistence_refreshes_after_pre_refresh_timeout tests/test_project_source_capabilities.py::test_wait_for_project_source_save_request_quiet_requires_relevant_requests_to_finish tests/test_project_source_capabilities.py::test_wait_for_project_source_save_request_quiet_rejects_committed_stale_inflight -q`
- `python3 -m pytest tests/test_project_source_capabilities.py tests/test_promptbranch_automation_service.py::test_profile_scoped_lock_serializes_services_sharing_profile tests/test_promptbranch_automation_service.py::test_profile_scoped_lock_reports_busy_before_client_timeout tests/test_promptbranch_automation_service.py::test_browser_status_reports_active_operation_and_profile_available -q`
- `python3 -m compileall -q .`
- ZIP root-layout and hygiene inspection

## Scope control

No slice or line was advanced. This repair changes only source-add verification and stale browser-profile/source-mutation diagnostics for the intended `v0.1.50` release line. It does not add new lifecycle routing, artifact adoption execution, policy sync execution, Git mutation, or new source mutation capability.
