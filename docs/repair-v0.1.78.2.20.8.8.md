# Repair v0.1.78.2.20.8.8 — Localhost source-add stale-inflight diagnostic timeout alignment

## Base release

`chatgpt_claudecode_workflow-2_v0.1.78.2.20.8.7.zip`

## Repair version

`v0.1.78.2.20.8.8`

## Reason

The `v0.1.78.2.20.8.7 --run-all-tests` release-control run passed live-profile preflight, ask-live, visual-artifact-roundtrip, release-live, import-smoke, and artifact guard, but failed adoption because `full_localhost` timed out in `project_source_add_text`.

The Docker service continued after the localhost client timed out and produced the structured fail-closed payload `post_commit_source_surface_not_refreshed` with `transaction_status=commit_seen_with_stale_inflight_not_verified_present`. The operator needs that structured result, not a generic client `ReadTimeout`, because the result includes release-blocking and recovery guidance.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `promptbranch_service_client.py`
- `promptbranch_full_integration_test.py`
- `tests/test_promptbranch_service_client.py`
- `tests/test_full_integration_harness.py`
- `tests/test_project_source_capabilities.py`
- `docs/project/definition-of-done.md`
- `docs/project/status.md`
- `docs/project/release-status.md`
- `docs/project/plan.md`
- `docs/project/decisions.md`
- `docs/project/migration.md`

## Behavior changes

- Project Source add service-client requests accept a per-call `request_timeout_seconds` override.
- Docker-service-backed full integration Project Source add calls use a source-mutation timeout floor of 900 seconds by default through `PROMPTBRANCH_SOURCE_MUTATION_SERVICE_TIMEOUT_SECONDS` / `CHATGPT_SOURCE_MUTATION_SERVICE_TIMEOUT_SECONDS`.
- The specific stale-inflight post-commit source-add failure remains release-blocking and operator-review-required.
- The full-integration harness attaches a retained-project `pb src list --json` diagnostic to `post_commit_source_surface_not_refreshed` / `commit_seen_with_stale_inflight_not_verified_present` failures before raising.

## Explicit non-changes

- No Project Source ambiguous persistence state is treated as success.
- No Project deletion path is re-enabled.
- No secure delete protocol is introduced.
- No artifact-current/adoption behavior changes.
- No prompt-file transport or response-completion semantics change.
- No normal release slice or line advances.

## Validation performed locally

```bash
python3 -m pytest -q \
  tests/test_promptbranch_service_client.py::test_add_project_source_uses_request_timeout_override \
  tests/test_full_integration_harness.py::test_docker_service_adapter_source_mutation_timeout_exceeds_general_client_timeout \
  tests/test_full_integration_harness.py::test_post_commit_source_failure_diagnostic_lists_retained_project_sources \
  tests/test_project_source_capabilities.py::test_text_post_commit_recovery_failure_reports_specific_status
```

Result: `4 passed`.

Full release-control, live browser release validation, and adoption/current verification were not run during candidate packaging.
