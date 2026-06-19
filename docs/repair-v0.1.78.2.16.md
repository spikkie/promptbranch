# Repair v0.1.78.2.16 — Project Source post-commit verification retry

## Base release

`v0.1.78.2.15`

## Repair version

`v0.1.78.2.16`

## Reason

`v0.1.78.2.15 --run-all-tests` progressed past Docker provenance, live profile, rate-limit, text-source compatibility isolation, and source-remove containment, but the localhost full transport failed at `project_source_overwrite_file` with `transaction_status=commit_seen_with_stale_inflight_not_verified_present`. The save request started and a commit was observed, but refreshed Project Source persistence proof did not complete before the release gate failed.

A later focused retry was contaminated by ChatGPT 429/rate-limit pressure and timed out before producing deterministic overwrite evidence. The repair keeps fail-closed behavior, but adds one bounded recovery path for the specific safe/ambiguous state where a file-source commit was observed, no save failure was observed, and stale inflight requests remained.

## Files changed

- `promptbranch_browser_auth/client.py`
- `tests/test_project_source_capabilities.py`
- `docs/repair-v0.1.78.2.16.md`
- `docs/project/definition-of-done.md`
- `docs/project/release-status.md`
- `docs/project/status.md`
- `docs/project/migration.md`
- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`

## Behavior

When file-source persistence verification times out after a mutation transaction reports `commit_seen_with_stale_inflight_not_verified_present`, Promptbranch now:

1. keeps the normal persistence verifier fail-closed;
2. enters a bounded post-commit recovery loop only for file sources;
3. reopens/refetches the Project Sources surface without waiting on persisted conversation-history cooldown;
4. re-lists source cards and verifies the requested source;
5. returns success only if refreshed proof is observed;
6. marks recovery with `verification_mode=post_commit_refresh_recovered` and `persistence_recovered_after_commit=true`;
7. still returns a release-blocking failure if the source is absent after the bounded recovery window.

## Validation performed

Focused local validation:

```text
pytest -q \
  tests/test_project_source_capabilities.py::test_add_project_source_operation_recovers_stale_inflight_post_commit_verification_timeout \
  tests/test_project_source_capabilities.py::test_post_commit_recovery_is_limited_to_stale_inflight_file_commit \
  tests/test_project_source_capabilities.py::test_add_project_source_operation_reports_removed_existing_when_overwrite_persistence_fails \
  tests/test_project_source_capabilities.py::test_add_project_source_operation_returns_persistence_false_negative_diagnostics \
  tests/test_project_source_capabilities.py::test_file_source_commit_stale_inflight_extends_persistence_readback
```

Result:

```text
5 passed
```

Additional packaging validation was run before handoff: compileall, shell syntax checks, ZIP integrity, ZIP hygiene, focused project-control/version/delete-safety tests, and Artifact Guardian.

## Scope confirmation

This is a repair release. It does not advance the normal slice or open `v0.1.79` work.

Preserved boundaries:

- no ChatGPT Project deletion;
- no secure delete protocol;
- no Project Source removal behavior expansion;
- no text-source compatibility promotion back into the default release gate;
- no Docker provenance weakening;
- no live seed or rate-limit policy expansion beyond the existing repair line.
