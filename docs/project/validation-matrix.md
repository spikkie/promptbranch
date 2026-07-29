# Validation Matrix

## Purpose

This file defines the required release-validation groups for `pb test full` and release-control evidence.

`pb test full` must not rely on operator memory for focused regression suites. The full/release validation report must declare which groups ran, which groups were skipped, and whether skipped groups are allowed.

## Required release-validation groups

| Group | Required | Purpose | Representative command |
|---|---:|---|---|
| `project_control_surface` | yes | Validate `docs/project/` structure, DoD table, release-status table, and next safe action. | `python3 -m pytest -q tests/test_project_control_surface.py` |
| `project_authority_behavioral_surface` | yes | Validate single-owner authority domains, runtime adopted-registry resolution, and the read-only instruction/skill/agent/tool/prompt inventory. | `python3 -m pytest -q tests/test_project_authority_graph.py tests/test_behavioral_surface.py` |
| `application_architecture_structural` | yes | Validate the tracked PBAI-001 declaration, all ten non-empty architecture layers, delegation, bounded authority, and proof-level reporting. | `python3 -m pytest -q tests/test_promptbranch_application_architecture.py` |
| `application_architecture_registry` | yes | Resolve the tracked PBAI-001 Agent, Skill, Tool, Validator, state, evidence, capability, and authority-controller registry without executing project code. | `python3 promptbranch_cli.py application architecture validate --repo-path . --level registry --json` |
| `version_surface` | yes | Validate `VERSION`, `pyproject.toml`, and `promptbranch_version.py` consistency. | `python3 -m pytest -q tests/test_promptbranch_version.py` |
| `artifact_json_contracts` | yes | Guard artifact adopt/current/baseline JSON contracts and external-repo reporting. | `python3 -m pytest -q tests/test_promptbranch_artifacts.py tests/test_promptbranch_cli.py -k "adopt or artifact_current or local_only or local_artifact_not_found or promptbranch_repo or baseline_status or mvp_status"` |
| `repo_project_registry` | yes | Guard project-scoped repo registry behavior and repo doctor/list invariants. | `python3 -m pytest -q tests/test_promptbranch_project.py tests/test_promptbranch_repos.py` |
| `browser_scheduler_source_lifecycle` | yes | Guard scheduler/source lifecycle behavior, same-profile queueing, browser busy diagnostics, and cleanup planning. | `python3 -m pytest -q tests/test_promptbranch_automation_service.py::test_profile_queue_default_matches_advertised_scheduler_timeout tests/test_promptbranch_automation_service.py::test_source_remove_waits_behind_source_list_with_same_profile tests/test_promptbranch_automation_service.py::test_project_remove_is_frozen_before_profile_scheduler tests/test_promptbranch_automation_service.py::test_browser_profile_busy_payload_marks_scheduler_path tests/test_promptbranch_cli.py::test_src_add_promotes_browser_profile_busy_to_top_level_payload tests/test_promptbranch_cli.py::test_queue_status_command_emits_scheduler_json tests/test_promptbranch_cli.py::test_release_lifecycle_plan_includes_scheduler_and_source_queue tests/test_promptbranch_cli.py::test_release_lifecycle_plan_blocks_when_artifact_current_is_stale tests/test_promptbranch_cli.py::test_src_list_browser_profile_busy_reports_wait_idle_guidance` |
| `release_lifecycle_plan` | yes | Guard release lifecycle plan and source queue integration invariants. | `python3 -m pytest -q tests/test_promptbranch_cli.py -k "release_lifecycle_plan"` |
| `execution_envelope_validation_gate` | yes | Recompute and validate the canonical v0.1.107 execution envelope while proving zero execution and mutation authority. | `python3 promptbranch_cli.py loop execution-envelope-validation --target examples/loop-targets/sandboxed-file-mutation-target.json --json` |
| `package_import_smoke` | yes | Validate installed package imports outside the source tree. | `pb test full` agent profile step `package_import_smoke` |
| `compileall` | yes | Validate Python source compilation. | `python3 -m compileall -q .` |
| `zip_hygiene` | yes | Validate candidate ZIP layout and generated/cache exclusions. | `pb test full` agent profile step `package_hygiene` |

## Reporting rule

The full-test JSON and post-release validation summary must include:

```text
release_validation_groups.ok
release_validation_groups.missing_required_groups
release_validation_groups.groups.<group>.ok
release_validation_groups.groups.<group>.command
```

If a required group is missing or failed, release-control must treat the full-test evidence as not green.

## Last updated

```text
v0.1.113
```


## v0.1.103.10.69 validation addition

`install.sh` is covered by shell-script static tests that verify the strict all-all release-control flags, adoption flag, log paths, and current-state verification command.


## v0.1.103.10.70 validation addition

- Static release-control classifier checks include `live_bootstrap_guardrail` and `skipped_blocked_by_live_bootstrap_guardrail` in the external-live blocked status set.
- Replay harness verifies live bootstrap guardrail returns final verdict `LIVE_BLOCKED` while downstream live steps remain skipped and artifact guard remains passable.

## v0.1.104 validation addition

The loop-focused release validation must cover:

- the successful mutate/verify/validate/rollback/delete sequence;
- non-sandbox path rejection;
- expected-after hash mismatch with successful rollback;
- sandbox validation failure with successful rollback;
- rollback failure classification and fail-closed result;
- unchanged repository fixture evidence;
- CLI JSON and text contracts for `promptbranch.loop.sandbox_mutation_verification`.

Representative command:

```bash
python3 -m pytest -q \
  tests/test_promptbranch_loop.py \
  tests/test_cli_loop.py
```
