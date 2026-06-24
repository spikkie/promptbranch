# Release v0.1.84.5.12.2 — repair: explicit release-validation group nodeids

## Type

Repair release for `v0.1.84.5.12`.

## Base release

`chatgpt_claudecode_workflow-2_v0.1.84.5.12.1.zip`

## Reason

The full release-control run for `v0.1.84.5.12.1` reached the offline release-validation group gate but `browser_scheduler_source_lifecycle` timed out after 300 seconds. The timed command used a broad pytest expression containing the generic selector term `cleanup`, which can select unrelated cleanup-oriented tests in operator environments and makes the release gate less deterministic than the group name implies.

This repair replaces the broad `-k` expression with explicit fast pytest nodeids that cover scheduler, source queue, browser-profile-busy, source-remove, and release-lifecycle-plan queue invariants. It also updates the validation matrix and adds regression coverage so the group cannot silently reintroduce the broad cleanup selector.

## Files changed

- `promptbranch_test_suite.py`
- `tests/test_promptbranch_test_suite.py`
- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `docs/project/validation-matrix.md`
- `docs/release-v0.1.84.5.12.2.md`
- `docs/project/decisions.md`
- `docs/project/status.md`
- `docs/project/release-status.md`
- `docs/project/migration.md`
- `docs/project/definition-of-done.md`
- `docs/project/plan.md`

## Scope boundary

No slice or line advanced. The active slice remains `v0.1.84.5.12 — Explicit new-task ask mode`.

No changes were made to:

- `pb ask --new-task` routing semantics
- composer no-fill safety
- Project Source mutation
- artifact adoption/current behavior
- ChatGPT Project deletion behavior
- live browser test semantics

## Validation

Focused repair validation:

```bash
python3 -m pytest -q tests/test_promptbranch_test_suite.py::test_browser_scheduler_release_validation_group_uses_explicit_fast_nodeids
python3 -m pytest -q tests/test_promptbranch_automation_service.py::test_profile_queue_default_matches_advertised_scheduler_timeout tests/test_promptbranch_automation_service.py::test_source_remove_waits_behind_source_list_with_same_profile tests/test_promptbranch_automation_service.py::test_project_remove_is_frozen_before_profile_scheduler tests/test_promptbranch_automation_service.py::test_browser_profile_busy_payload_marks_scheduler_path tests/test_promptbranch_cli.py::test_src_add_promotes_browser_profile_busy_to_top_level_payload tests/test_promptbranch_cli.py::test_queue_status_command_emits_scheduler_json tests/test_promptbranch_cli.py::test_release_lifecycle_plan_includes_scheduler_and_source_queue tests/test_promptbranch_cli.py::test_release_lifecycle_plan_blocks_when_artifact_current_is_stale tests/test_promptbranch_cli.py::test_src_list_browser_profile_busy_reports_wait_idle_guidance
python3 -m compileall -q promptbranch_test_suite.py promptbranch_cli.py promptbranch_container_api.py promptbranch_browser_auth promptbranch_automation promptbranch_service_client.py
```

Full release-control/adoption was not run in the assistant environment.
