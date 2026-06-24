# Release v0.1.85 — Ask state observability and new-task proof hardening

## Baseline

- Accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.84.5.12.2.zip`
- Baseline status: accepted/current by operator-provided release-control/adoption/current evidence.

## Scope

This release hardens operator observability after the explicit `pb ask --new-task` slice.

In scope:

- Make `pb state` print schema-version and current schema-v2 conversation fields.
- Add `pb state --proof` for read-only proof metadata around `.current.conversation_url`.
- Add `scripts/smoke-pb-ask-new-task.sh` as the canonical short live smoke for the new-task state-binding proof.
- Add focused tests ensuring operators and scripts use `.current.conversation_url`, not stale top-level `.conversation_url`.

Out of scope:

- No ChatGPT browser behavior change.
- No Project Source mutation behavior change.
- No artifact adoption/current behavior change.
- No Project deletion behavior change.
- No backend API investigation.
- No MkDocs deployment/release-package integration.

## Behavior

`pb state` now includes:

- `schema_version`
- `current_project_home_url`
- `current_conversation_url`
- `current_conversation_id`
- `current_updated_at`
- `current_conversation_url_json_path=.current.conversation_url`

`pb state --proof --json` emits a read-only proof payload with schema-v2 state paths and the new-task smoke state-check contract.

The canonical short smoke is:

```bash
scripts/smoke-pb-ask-new-task.sh
```

It verifies:

- `pb ask --new-task` returns the sentinel token.
- `.current.conversation_url` is populated.
- `.current.conversation_url` changes from the pre-run value.

## Validation run for candidate handoff

Focused validation run during candidate creation:

```bash
python3 -m pytest -q \
  tests/test_cli_state.py::test_state_snapshot_exposes_schema_v2_current_paths \
  tests/test_cli_state.py::test_main_state_text_exposes_current_conversation_schema_v2_path \
  tests/test_cli_state.py::test_main_state_proof_json_reports_new_task_state_check \
  tests/test_promptbranch_shell_scripts.py::test_new_task_smoke_script_uses_schema_v2_current_conversation_path \
  tests/test_ask_cli_new_task.py \
  tests/test_ask_busy_conversation.py \
  tests/test_promptbranch_version.py \
  tests/test_project_control_surface.py
```

Additional local checks:

```bash
python3 -m compileall -q promptbranch_state.py promptbranch_cli.py promptbranch_container_api.py promptbranch_browser_auth promptbranch_automation promptbranch_service_client.py
bash -n scripts/smoke-pb-ask-new-task.sh
bash -n chatgpt_claudecode_workflow_release_control.sh
python3 promptbranch_cli.py state --help
```

## Acceptance requirement

This candidate is not accepted/current until full release-control passes and `pb artifact current --json` proves runtime/source/artifact/registry consistency.
