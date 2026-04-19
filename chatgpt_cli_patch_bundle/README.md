# ChatGPT CLI / Service Patch Bundle

This bundle is a **targeted patch plan** for the repo that produced the logs under:

- `chatgpt_browser_auth/client.py`
- `chatgpt_automation/automation.py`
- `chatgpt_automation/service.py`
- `chatgpt_container_api.py`
- `chatgpt_service_client.py`
- `chatgpt_cli.py`

It addresses two concrete defects observed in the test runs:

1. `ask --json` crashes in `chatgpt_browser_auth/client.py` because `candidate_text` is referenced before assignment in `_wait_and_get_json`.
2. `ask` has no conversation targeting option, so a second `ask` against a project page opens a new conversation instead of replying in the first one.

## Intended outcome

After these changes, this exact flow should be testable end-to-end:

1. `login-check`
2. `project-create`
3. `project-resolve`
4. `project-ensure`
5. `project-source-add`
6. `ask --json <prompt>` -> returns `conversation_url`
7. `ask --json --conversation-url <captured_url> <prompt>` -> stays in the same chat
8. `shell`
9. `project-source-remove`
10. `project-remove`

## Files in this bundle

- `patch_plan.md` — detailed change set by file
- `chatgpt_cli_sequence_v5.py` — updated harness that requires `--conversation-url`
- `expected_contract.json` — minimal request/response contract for the new option

## Important boundary

This bundle was prepared from runtime logs and CLI behavior, **not from the repo source itself**. The uploaded zips in this conversation do not contain the ChatGPT CLI/service source tree. Apply these changes inside your real `chatgpt_claudecode_workflow` repo.
