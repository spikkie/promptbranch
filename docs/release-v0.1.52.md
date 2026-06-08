# Release v0.1.52

## Base

Built from accepted baseline `chatgpt_claudecode_workflow-2_v0.1.50.5.zip`.

## Purpose

Integrate the read-only backend diagnostic commands from the v0.1.51 candidate and remove the recurring Docker Compose hardcoded service-image version drift.

## Changes

- Added read-only backend diagnostics:
  - `pb debug backend --json`
  - `pb debug backend projects --json`
  - `pb debug backend conversations --json`
- Changed `docker-compose.chatgpt-service.yml` to use `PROMPTBRANCH_SERVICE_IMAGE_TAG` instead of a static release tag.
- Updated release-control and service runner scripts to derive `PROMPTBRANCH_SERVICE_IMAGE_TAG` from the repo `VERSION` file by default.
- Updated version-consistency validation so Docker Compose image tags are no longer treated as release-version source metadata.
- Updated tests to guard against reintroducing hardcoded Compose release tags.

## Validation

Focused validation performed:

- `python -m compileall promptbranch_backend_reads.py promptbranch_cli.py promptbranch_test_suite.py chatgpt_container_api.py promptbranch_container_api.py`
- `pytest tests/test_promptbranch_backend_reads.py tests/test_compose_timeout_policy.py tests/test_chatgpt_container_api.py tests/test_promptbranch_container_api.py tests/test_promptbranch_test_suite.py -q`
- `pytest tests/test_promptbranch_shell_scripts.py::test_release_control_uses_single_default_runtime_identity -q`
- `pytest tests/test_promptbranch_shell_scripts.py::test_release_control_recreates_docker_service_and_verifies_version -q`
- `pytest tests/test_promptbranch_shell_scripts.py::test_docker_service_runs_as_host_user_to_avoid_root_owned_artifacts -q`

## Scope boundary

No backend writes were added. Source sync and artifact adoption behavior were not changed.
