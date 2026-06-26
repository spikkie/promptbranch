# Repair v0.1.93.1 — Direct release-validation scheduler nodeid isolation

## Type

Repair-only candidate for `v0.1.93`.

## Base

```text
base candidate: chatgpt_claudecode_workflow-2_v0.1.93.zip
latest accepted/current before this repair: chatgpt_claudecode_workflow-2_v0.1.92.zip
repair version: v0.1.93.1
```

## Reason

The `v0.1.93 --run-all-tests --adopt-after-validation` run validated most of the planned-action walkthrough candidate but failed the `full_direct` step. The failure was isolated to the required release-validation group `browser_scheduler_source_lifecycle` timing out at this nodeid:

```text
tests/test_promptbranch_automation_service.py::test_source_remove_waits_behind_source_list_with_same_profile
```

The same nodeid group later passed under the localhost leg, which means the planned-action feature was not the defect. The failure mode pointed at release-validation subprocess isolation after direct live browser/source work had left ambient profile/source lock state visible in the environment.

## Scope

This repair preserves the `v0.1.93` planned-action walkthrough and changes only release-validation group isolation/diagnostics.

In scope:

- Strip all inherited `CHATGPT_*` environment variables from offline release-validation pytest subprocesses.
- Strip live Promptbranch service/image/version/profile-seed variables from offline release-validation pytest subprocesses.
- Remove inherited `PYTEST_ADDOPTS` so the release gate owns its nodeids/options.
- Run each `browser_scheduler_source_lifecycle` nodeid with isolated `HOME`, `TMPDIR`, XDG directories, and a release-validation profile directory.
- Record ambient repo `.pb_profile/.promptbranch-browser-profile.lock` snapshot in per-nodeid group diagnostics.
- Preserve per-nodeid progress, active-nodeid timeout reporting, and the same explicit 9 required scheduler/source nodeids.

Out of scope:

- No loop/planned-action behavior changes.
- No live/browser behavior changes.
- No adoption/current semantic changes.
- No Project Source mutation semantic changes.
- No Project deletion behavior changes.
- No Docker bootstrap changes.
- No broad timeout increase.

## Validation performed

Focused validation for this candidate should cover:

```text
python3 -m pytest -q \
  tests/test_promptbranch_test_suite.py::test_release_validation_group_strips_browser_service_env \
  tests/test_promptbranch_test_suite.py::test_release_validation_group_nodeid_progress_reports_completed_nodeids \
  tests/test_promptbranch_test_suite.py::test_release_validation_group_nodeid_progress_timeout_reports_active_nodeid \
  tests/test_promptbranch_test_suite.py::test_release_validation_nodeid_progress_records_ambient_profile_lock \
  tests/test_promptbranch_automation_service.py::test_source_remove_waits_behind_source_list_with_same_profile \
  tests/test_promptbranch_loop.py \
  tests/test_cli_loop.py \
  tests/test_promptbranch_version.py \
  tests/test_project_control_surface.py
```

Full release-control adoption proof remains required before treating this repair as accepted/current.

## Slice advancement

No normal slice advances in this repair. `v0.1.93.1` repairs the intended `v0.1.93` release-validation defect only.
