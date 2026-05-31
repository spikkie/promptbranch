# Release v0.0.278.86

## Purpose

Harden the live browser integration cleanup path after v0.0.278.85 proved the deterministic `pb test artifact-roundtrip` check but exposed profile-lock contention during final temporary-project cleanup.

## Changes

- Retry `project_remove_cleanup` when the browser service reports `browser_profile_busy`.
- Treat browser-profile contention during cleanup as a transient retryable condition before failing the suite.
- Preserve structured cleanup retry evidence in `cleanup_steps`.
- Surface cleanup failures in raw `pb test` suite summaries via `failure_count` and `failed_steps`.
- Include cleanup failures in `pb test report` section and suite failure summaries.

## Boundaries

- Does not change deterministic `pb test artifact-roundtrip` behavior.
- Does not add visual/live artifact roundtrip to default full tests.
- Does not relax browser integration assertions.
- Does not adopt or mutate artifact state.
