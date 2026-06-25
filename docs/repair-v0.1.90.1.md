# Repair v0.1.90.1 — Project source overwrite stale-inflight post-commit recovery repair

## Base release

```text
base candidate: chatgpt_claudecode_workflow-2_v0.1.90.zip
repair version: v0.1.90.1
accepted/current before repair: chatgpt_claudecode_workflow-2_v0.1.89.zip
```

## Repair reason

`v0.1.90` installed successfully and its global conversation-history request shield worked: live validation reported no conversation-history 429, no rate-limit modal, and no cooldown waits. The release was still not adopted because `project_source_overwrite_file` failed after a file-source commit was observed while one save request remained inflight.

The failed result was release-blocking and reported:

```text
status: post_commit_source_surface_not_refreshed
transaction_status: commit_seen_with_stale_inflight_not_verified_present
save_started: 2
save_finished: 1
save_failed: 0
save_inflight: 1
post_commit_recovery.status: not_recovered
```

The same run showed a minimal observed click path, so the failure was not caused by repeated or fallback clicks.

## Changes

- Preserve the `v0.1.90` global conversation-history auto-request shield.
- Require file-source uploads/overwrites to reach normal save-request quiet before post-save persistence verification; do not use stale-inflight soft quiet for file uploads.
- Keep stale-inflight soft quiet for text sources, where the post-refresh proof remains the controlling verification boundary.
- Add a post-commit visible-snapshot recovery path: if the stronger recovery loop times out but the current Project Sources surface visibly contains the requested source after a commit and no save failure, classify the source as recovered instead of returning a false negative.
- Add explicit failure classification for true absence after stale-inflight recovery: `post_commit_source_absent_after_stale_inflight`.
- Include `post_commit_visible_match_found` and `post_commit_source_absent_after_recovery` in fail-closed diagnostics.

## Scope boundaries

This repair does not advance the `v0.1.90` feature scope. It does not change:

- adoption/current semantics;
- Project deletion behavior;
- Project Source add/remove authority model;
- loop behavior;
- deployment/Kubernetes behavior;
- evidence-reuse scope from `v0.1.88`.

## Validation

Focused validation must include:

```text
tests/test_project_source_capabilities.py::test_file_project_source_add_waits_for_normal_quiet_not_stale_soft_quiet
tests/test_project_source_capabilities.py::test_add_file_source_operation_recovers_post_commit_visible_snapshot_after_recovery_timeout
tests/test_project_source_capabilities.py::test_stale_inflight_post_commit_absent_source_is_classified_as_true_absence
```

Additional regression validation should include version/control-surface tests, loop tests, compileall, shell syntax, Artifact Guardian, artifact verify, and ZIP hygiene.

## Acceptance requirement

`v0.1.90.1` is not accepted/current until release-control validation and `pb artifact current --json` prove runtime, source, artifact, registry current, and consistency alignment.
