# Release v0.1.74

## Type

```text
normal candidate
```

## Baseline

```text
chatgpt_claudecode_workflow-2_v0.1.73.4.zip
```

## Slice

```text
Release validation suite coverage manifest
```

## Goal

Make release-control/full-test validation explicitly declare and run the focused regression groups that protected the v0.1.73.x repair line:

- artifact/adoption/current JSON contracts;
- external repo current-state reporting;
- scheduler/source lifecycle behavior;
- project control-surface validation;
- version-surface validation;
- compileall, package import smoke, and ZIP hygiene.

## In scope

- Add `docs/project/validation-matrix.md`.
- Add release-validation group metadata to `promptbranch_test_suite.py`.
- Run required release-validation groups from the full-test agent profile.
- Include release-validation group status in `pb test report` output.
- Include release-validation group status in release-control structured summaries.
- Add focused tests for the validation manifest/reporting behavior.
- Update `docs/project/` status, DoD, plan, release-status, and decisions.

## Out of scope

- Browser automation behavior changes.
- Project Source semantics changes.
- Artifact adoption/current semantics changes.
- Multi-repo registry behavior changes.
- Deployment/Docker behavior changes.
- Broad pytest cleanup beyond release-validation coverage.

## Validation

Focused validation for this candidate should include:

```bash
python3 -m pytest -q tests/test_promptbranch_test_suite.py tests/test_promptbranch_test_report.py
python3 -m pytest -q tests/test_promptbranch_artifacts.py tests/test_promptbranch_cli.py -k "adopt or artifact_current or local_only or local_artifact_not_found or promptbranch_repo or baseline_status or mvp_status"
python3 -m pytest -q tests/test_promptbranch_automation_service.py tests/test_promptbranch_service_client.py tests/test_promptbranch_cli.py -k "scheduler or profile_busy or queue_wait or source_remove or cleanup or release_lifecycle_plan"
python3 -m pytest -q tests/test_promptbranch_project.py tests/test_promptbranch_repos.py tests/test_project_control_surface.py tests/test_promptbranch_version.py
python3 -m compileall -q .
```

Full acceptance still requires release-control and adoption evidence.
