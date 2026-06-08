# Release v0.1.53

## Scope

Normal incremental release from `chatgpt_claudecode_workflow-2_v0.1.52.zip`.

This release fixes the full-test `browser.project_source_overwrite_file` contention path without changing backend diagnostics or VERSION-derived Docker Compose image tagging.

## Changes

- Source mutation operations now use a bounded 120-second profile wait in the full integration harness.
- Docker-service source-add calls pass `profile_lock_wait_seconds` explicitly so the service serializes fresh `add_project_source` / overwrite contention instead of failing after the old 30-second default.
- The Docker-service full integration adapter retries fresh same-family source-mutation `browser_profile_busy` responses with bounded backoff.
- Stale source locks are not retried by the adapter; stale-lock recovery remains owned by the service lock layer.
- Container API health tests now assert against `promptbranch_version.PACKAGE_VERSION` instead of embedding a release literal.

## Validation

Focused validation performed during artifact build:

```text
pytest tests/test_full_integration_harness.py tests/test_promptbranch_container_api.py tests/test_chatgpt_container_api.py tests/test_compose_timeout_policy.py -q
python -m compileall promptbranch_full_integration_test.py promptbranch_container_api.py chatgpt_container_api.py promptbranch_version.py
```

## Boundary

No backend diagnostic behavior changed.
No VERSION-derived Docker Compose image-tag behavior changed.
No source-sync semantics changed outside full-test browser profile serialization/retry behavior.
