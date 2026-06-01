# Release v0.1.1.1 — Single-default runtime repair

## Baseline

```text
chatgpt_claudecode_workflow-2_v0.1.1.zip
```

## Repair version

```text
chatgpt_claudecode_workflow-2_v0.1.1.1.zip
```

## Reason

`v0.1.1` separated artifact identity from Docker runtime identity, but it widened runtime behavior into multi-instance operation. That made local worktree testing depend on `COMPOSE_PROJECT_NAME`, `PROMPTBRANCH_SERVICE_PORT`, and `CHATGPT_SERVICE_BASE_URL` propagation. The project direction is now single-default runtime per machine: one Docker stack, one installed Promptbranch package, one service URL, and one active branch/version at a time.

## Files changed

```text
VERSION
pyproject.toml
promptbranch_version.py
chatgpt_claudecode_workflow_release_control.sh
docker-compose.chatgpt-service.yml
run_chatgpt_service.sh
run_chatgpt_service_dev.sh
promptbranch_test_suite.py
tests/test_promptbranch_test_suite.py
tests/test_promptbranch_shell_scripts.py
docs/release-v0.1.1.1.md
```

## Behavior

- Artifact prefix handling from `--install-from-zip` is preserved, so `chatgpt_claudecode_workflow-2_v0.1.1.zip` repairs to `chatgpt_claudecode_workflow-2_v0.1.1.1.zip`.
- Runtime identity is single-default again:
  - Compose project: `chatgpt_claudecode_workflow`
  - Service port: `8000`
  - Service base URL: `http://localhost:8000`
- Release-control exports `CHATGPT_SERVICE_BASE_URL=http://localhost:8000` before running `pb test full` and `pb test report`.
- Docker Compose image declaration is static and versioned for source-version consistency.
- Version-consistency parsing also accepts the earlier parameterized Compose image default so historical/candidate checks do not report `docker_compose.chatgpt_service.image = null`.

## Validation performed

```text
bash -n chatgpt_claudecode_workflow_release_control.sh
python3 scripts/orchestration/validate_examples.py
python3 -m pytest -q tests/orchestration/test_orchestration_examples.py
python3 -m pytest -q tests/test_promptbranch_test_suite.py::test_source_version_consistency_accepts_parameterized_compose_default tests/test_promptbranch_test_suite.py::test_source_version_consistency_detects_parameterized_compose_default_drift tests/test_promptbranch_test_suite.py::test_source_version_consistency_detects_compose_image_tag_drift tests/test_promptbranch_shell_scripts.py::test_release_control_uses_single_default_runtime_identity
python3 -m compileall -q .
ZIP reopen / VERSION / wrapper / hygiene verification
```

## Scope confirmation

This is a repair release only. It does not advance the JSON Orchestration State MVP, open a new line, add new orchestration commands, or change planned MVP scope.
