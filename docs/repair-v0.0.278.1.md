# Repair v0.0.278.1 — Browser Profile Global Lock

## Base release

```text
chatgpt_claudecode_workflow_v0.0.278.zip
```

## Repair version

```text
v0.0.278.1
```

## Reason

A live timeout incident showed `pb ask` and project source operations overlapping while using the same persistent browser profile directory. The baseline had an instance-level `asyncio.Lock`, but the container API can create multiple `ChatGPTAutomationService` instances for different project URLs that still point to the same `/app/.pb_profile`.

That made the instance-level lock insufficient. Browser/profile operations must be serialized by resolved profile directory, not by service instance.

## Files changed

```text
VERSION
pyproject.toml
promptbranch_version.py
promptbranch.egg-info/PKG-INFO
docker-compose.chatgpt-service.yml
promptbranch_automation/service.py
promptbranch_container_api.py
docs/browser-session-manager-async-jobs-design.md
docs/repair-v0.0.278.1.md
tests/test_promptbranch_automation_service.py
tests/test_promptbranch_container_api.py
tests/test_chatgpt_container_api.py
tests/test_cli_parser.py
tests/test_compose_timeout_policy.py
tests/test_promptbranch_cli.py
```

## Functional changes

- Replaced the per-service-instance browser lock with a profile-scoped async-compatible lock.
- The lock is keyed by resolved profile directory.
- The lock also uses an advisory file lock at `.promptbranch-browser-profile.lock` inside the profile directory for cross-process protection.
- Container service default for `CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS` is now false.
- Added a design document for the intended long-term `BrowserSessionManager + async job records + backend-first reads + transactional mutation queue` solution.

## Validation performed

```text
python3 -m py_compile promptbranch_automation/service.py promptbranch_container_api.py promptbranch_version.py
python3 -m py_compile <all repository Python files>
pytest -q tests/test_promptbranch_automation_service.py tests/test_promptbranch_container_api.py tests/test_chatgpt_container_api.py tests/test_cli_parser.py tests/test_compose_timeout_policy.py tests/test_promptbranch_cli.py::test_main_version_subcommand_outputs_release tests/test_promptbranch_cli.py::test_phase1_doctor_reports_state_without_mutating tests/test_promptbranch_cli.py::test_release_doctor_reports_runtime_source_mismatch_read_only tests/test_promptbranch_cli.py::test_release_doctor_artifact_zip_hardening_reports_candidate_phase tests/test_promptbranch_cli.py::test_release_doctor_blocks_runtime_version_file_mismatch -q
```

## Scope confirmation

No normal release line, slice, or planned scope was advanced.

This repair fixes a defect in the intended `v0.0.278` behavior: safe browser profile ownership during browser-backed operations.
