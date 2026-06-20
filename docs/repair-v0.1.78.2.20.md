# Repair note — v0.1.78.2.20

## Base release

- Accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.78.2.16.zip`
- Superseded repair candidates carried forward: `v0.1.78.2.17`, `v0.1.78.2.18`, `v0.1.78.2.19`
- Repair version: `v0.1.78.2.20`

## Reason

The operator live smoke for `v0.1.78.2.19` showed that the prompt-file ask reached the browser and ChatGPT successfully:

- `pb ask` exited `0`.
- `submit_method` was `button_click` in nested evidence.
- `submit_message_request_observed` was true in nested evidence.
- The response matched the injected freshness nonce.
- `prepare_token_set_not_consumed` was false.

The smoke still failed because the harness expected the whole answer to equal a raw string, while `pb ask --json` asks the assistant for strict JSON and returns the token as `answer.token`. The successful ask JSON also exposed key submit-causality fields only in nested structures, leaving top-level fields such as `prefer_button_submit` and `submit_method` null.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `promptbranch_browser_auth/client.py`
- `scripts/smoke-pb-ask-prompt-file.sh`
- `tests/test_promptbranch_shell_scripts.py`
- `tests/test_project_list_browser_client.py`
- `docs/project/definition-of-done.md`
- `docs/project/status.md`
- `docs/project/release-status.md`
- `docs/project/decisions.md`
- `docs/project/migration.md`
- `docs/repair-v0.1.78.2.20.md`

## Validation performed

Focused local validation was performed for the prompt-file smoke/source contract, project-control surface, Python compilation, shell syntax, ZIP integrity, and ZIP hygiene.

Full release-control, live smoke, and artifact adoption were not run in this environment.

## Scope confirmation

This is a repair release only. It does not advance the normal slice, does not change CV generator code, does not change Project Source add/remove behavior, does not change project deletion behavior, does not redesign retry/backoff, and does not mutate artifact-current state.
