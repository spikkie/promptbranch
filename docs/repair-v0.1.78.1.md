# Repair v0.1.78.1 — Project Source mutation transaction hardening

## Base release

```text
chatgpt_claudecode_workflow-2_v0.1.78.zip
```

## Repair version

```text
v0.1.78.1
```

## Reason

The v0.1.78 release-control run installed the AG-001 candidate and verified the Docker service version, but failed the live browser full-test in `project_source_add_file`.

The observed failure class was:

```text
status: persistence_not_verified
source_kind: file
persistence_verified: false
persistence_false_negative_possible: true
save_request_summary.started: 2
save_request_summary.finished: 1
save_request_summary.failed: 0
save_request_summary.saw_commit: true
save_request_summary.inflight: 1
```

The failure showed two defects in the intended release validation surface:

1. File Project Source persistence readback did not have an explicit transaction classification for `commit seen, stale inflight, but refreshed source card not verified`.
2. The full integration harness recorded a returned `{ok: false}` step result as a successful step until the later assertion raised, which could produce weak `failure_count` / `failed_steps` evidence.

## Files changed

```text
promptbranch_browser_auth/client.py
tests/test_project_source_capabilities.py
promptbranch_full_integration_test.py
tests/test_full_integration_harness.py
VERSION
pyproject.toml
promptbranch_version.py
tests/test_promptbranch_version.py
docs/repair-v0.1.78.1.md
docs/project/definition-of-done.md
docs/project/plan.md
docs/project/status.md
docs/project/release-status.md
docs/project/decisions.md
docs/project/migration.md
```

## Repair behavior

```text
- Adds explicit Project Source mutation transaction classification.
- Classifies commit-seen/stale-inflight/not-visible as release-blocking ambiguous state.
- Extends post-commit file-source readback attempts only for file sources with commit evidence.
- Keeps final persistence proof fail-closed: source must still be verified on the refreshed Sources surface.
- Ensures integration steps returning `{ok:false}` are recorded as failed steps immediately.
```

## Out of scope preserved

```text
- No AG-001 guard behavior changes.
- No pb artifact build integration.
- No pb artifact heal.
- No pb artifact agent.
- No lifecycle integration.
- No assistant-side handoff enforcement.
- No adoption/current changes.
- No k8s-game docs, schemas, state machines, drawio roadmap, or runtime work.
```

## Validation performed

```text
python3 -m pytest -q tests/test_project_source_capabilities.py -k 'file_source_commit_stale or transaction_classifies or persistence_false_negative'
python3 -m pytest -q tests/test_full_integration_harness.py -k 'run_step_marks_returned_false_result_as_failed or step_selection'
python3 -m pytest -q tests/test_project_control_surface.py tests/test_promptbranch_version.py
python3 -m compileall -q .
bash -n chatgpt_claudecode_workflow_release_control.sh scripts/post-release-validation.sh
```

## Slice / line movement

```text
No normal slice advanced.
No release line advanced.
v0.1.79 remains the next planned normal slice after v0.1.78 is accepted/current.
```
