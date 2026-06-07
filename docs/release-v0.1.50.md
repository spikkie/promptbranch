# Release v0.1.50 — Release lifecycle scheduler integration

## Scope

`v0.1.50` integrates the native release lifecycle plan with the Promptbranch scheduler/resource-lock model and the source upload queue plan.

This is still planning/verification-only for the scheduler integration. It does not route live lifecycle execution through a new executor.

## Added

- `promptbranch_release_scheduler.py`
- release lifecycle scheduler plan embedded in `pb release lifecycle --plan --json`
- `--dry-run` alias for `pb release lifecycle --plan`
- explicit `--workspace-url`, `--account-id`, and `--service-id` planning context for lifecycle locks
- source upload queue plan embedded in the lifecycle plan
- regression tests for lifecycle scheduler/source-queue integration

## Safety boundary

The lifecycle plan now exposes these required serialization surfaces:

```text
git_repo:{repo_path}:exclusive
artifact:{repo_id}:exclusive
workspace:{project_id}:write
sources:{project_id}:exclusive
service_profile:{service_id}:exclusive
```

The Project Source upload phase delegates to the same source queue plan introduced in `v0.1.49`.

No install, source upload, acceptance hook execution, adoption, policy sync, Git commit, or Git push is performed in plan mode.

## Validation

Focused validation used for the release candidate:

```bash
python3 -m pytest -q tests/test_promptbranch_release_lifecycle_scheduler.py \
  tests/test_cli_parser.py::test_parser_accepts_release_lifecycle_dry_run_scheduler_context \
  tests/test_promptbranch_cli.py::test_release_lifecycle_plan_includes_scheduler_and_source_queue

python3 -m compileall -q .

pb release lifecycle --dry-run --json \
  --artifact ./chatgpt_claudecode_workflow-2_v0.1.50.zip \
  --version v0.1.50 \
  --workspace-url https://chatgpt.com/g/g-p-demo/project \
  | python3 -m json.tool
```

