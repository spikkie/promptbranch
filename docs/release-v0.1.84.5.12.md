# Release v0.1.84.5.12 — Explicit new-task ask mode

## Baseline

`chatgpt_claudecode_workflow-2_v0.1.84.5.11.zip`.

## Scope

Add explicit operator-controlled `pb ask --new-task` / `--new-conversation` support so an ask can start a fresh ChatGPT Project task from the remembered Project home instead of continuing the remembered task conversation.

## Changes

- Added `pb ask --new-task` with `--new-conversation` as an alias.
- Preserved default `pb ask` behavior: without the flag, Promptbranch continues to use the remembered conversation when one is present.
- Made `--new-task` ignore the remembered conversation URL and route the browser/service ask through the remembered Project home URL.
- Added structured invalid-argument handling for `--new-task --conversation-url` with `error_type=mutually_exclusive_conversation_target`.
- Added fail-closed handling when `--new-task` is requested but no Project home URL is known.
- Added state-update gating so a successful new-task ask updates the remembered conversation only after a returned conversation URL is in the expected Project and submission evidence is present.
- Preserved the existing no-fill composer invariant and reclassified a busy remembered conversation as `target_conversation_busy` when stop/thinking/interrupted blockers are visible.
- Preserved lower-level composer diagnostics through service responses.

## Out of scope

- Project Source mutation.
- Artifact adoption/current behavior.
- Project deletion.
- Broad release-control workflow changes.
- Interpreting literal prompt text such as `new task` as a command.

## Focused validation

```bash
pytest -q tests/test_ask_cli_new_task.py tests/test_ask_busy_conversation.py
pytest -q \
  tests/test_ask_cli_new_task.py \
  tests/test_ask_busy_conversation.py \
  tests/test_promptbranch_cli.py::test_main_can_ask_via_service_backend \
  tests/test_promptbranch_cli.py::test_main_can_ask_via_service_backend_from_env \
  tests/test_promptbranch_service_client.py::test_ask_result_includes_conversation_url_form_field \
  tests/test_promptbranch_container_api.py::test_ask_response_preserves_rate_limit_telemetry \
  tests/test_project_list_browser_client.py::test_wait_for_composer_ready_before_fill_rejects_stop_button \
  tests/test_project_list_browser_client.py::test_wait_for_composer_ready_before_fill_rejects_interrupted_answer
python3 -m compileall -q promptbranch_cli.py promptbranch_container_api.py promptbranch_browser_auth promptbranch_automation promptbranch_service_client.py
python3 promptbranch_cli.py ask --help | grep -E -- '--new-task|--new-conversation'
```

## Adoption status

Candidate only until release-control validation and `pb artifact current --json` prove current/adopted state.
