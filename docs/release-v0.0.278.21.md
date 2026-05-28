# Release v0.0.278.21

## Base

Built incrementally from `chatgpt_claudecode_workflow_v0.0.278.20.zip`.

## Reason

`v0.0.278.20` correctly failed closed when submit causality could not be proven, but it still depended on DOM turn selectors for proof. On warm, virtualized old tasks those selectors can report zero user and assistant turns even after the composer clears. This release adds backend task-message inspection as the preferred submit-causality proof.

## Changes

- Added backend `/backend-api/conversation/<conversation_id>` task-message inspection during submit confirmation.
- Matched the current prompt marker/request marker against backend user messages before entering response extraction.
- Preserved strict rejection of URL-only submit confirmation.
- Preserved `.19` request-marker response freshness guard.
- Preserved warm-task hydration reuse.
- Added evidence fields for backend task-message causality:
  - `submit_backend_task_message_found`
  - `submit_backend_task_message_seconds`
  - `submit_backend_task_message_status`
  - `backend_task_message_evidence`

## Validation

- `python3 -m py_compile promptbranch_browser_auth/client.py tests/test_project_list_browser_client.py`
- `pytest -q tests/test_project_list_browser_client.py`
- `pytest -q tests/test_chatgpt_container_api.py tests/test_promptbranch_container_api.py tests/test_cli_parser.py::test_parser_accepts_version_subcommand tests/test_compose_timeout_policy.py tests/test_promptbranch_cli.py::test_main_version_subcommand_outputs_release`

## Scope control

No slice or line was advanced. This release only hardens submit-causality verification for the intended `v0.0.278` ask-path optimization line.
