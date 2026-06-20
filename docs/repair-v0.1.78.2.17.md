# Repair v0.1.78.2.17 — `pb ask --prompt-file` button-first causal submit

## Base release

- Base release: `v0.1.78.2.16`
- Repair release: `v0.1.78.2.17`
- Release type: repair
- Scope: narrow Promptbranch submit-handling repair for `pb ask --prompt-file`

## Reason

`v0.1.78.2.16` preserved the `--prompt-file` content by merging it into the prompt text before browser submission, but it did not preserve the fact that the prompt originated from a prompt file. The browser layer therefore kept the keyboard-primary submit policy for prompt-file-only calls. Live evidence showed that keyboard Enter could produce a prepare-token-only state without a backend message commit, causing `prepare_token_set_not_consumed` and an empty answer.

Prompt-file based live workflows require deterministic button-first dispatch when ChatGPT exposes an enabled send button, followed by causal submit proof before answer waiting.

## Files changed

- `promptbranch_cli.py`
  - Carries `prefer_button_submit=True` when `pb ask` / `pb ask-release` receives `--prompt-file`.
  - Carries the same flag through ask-live prompt-file steps.
  - Exposes prompt-file submit preference in ask-live step evidence.
- `promptbranch_service_client.py`
  - Sends `prefer_button_submit=true` to the service API when requested.
- `promptbranch_container_api.py`
  - Accepts the `prefer_button_submit` form field and forwards it to the service.
  - Adds top-level submit diagnostic fields to the ask response model.
- `promptbranch_automation/service.py`
  - Forwards `prefer_button_submit` from API/service callers into the browser bot.
- `promptbranch_browser_auth/client.py`
  - Uses button-first submit whenever `prefer_button_submit` or attachments are present.
  - Keeps prepare-token-only states fail-closed.
  - Flattens submit-causality diagnostics on submit failure.
- `scripts/smoke-pb-ask-prompt-file.sh`
  - Adds an operator-run focused live smoke for `pb ask "Use the prompt file." --prompt-file ... --json`.
- Tests under `tests/`
  - Add focused coverage for CLI flag propagation, service form payload, API forwarding/diagnostics, browser button-first submit, failure diagnostics, ask-live prompt-file propagation, and smoke script contract.
- Project control surface files under `docs/project/`
  - Record repair status, DoD movement, release status, migration note, and decision rationale.

## Behavior after repair

When `pb ask` or `pb ask-release` is invoked with `--prompt-file`, Promptbranch now sets:

```json
{
  "prefer_button_submit": true
}
```

The browser submit layer then attempts the send button before keyboard Enter when a visible/enabled send button is available. Keyboard Enter remains a fallback only when the button path is unavailable or fails before dispatch.

`prepare_token_set_not_consumed` remains a hard failure. It is not treated as success, partial success, or answer timeout.

Failure JSON now includes submit evidence such as:

```json
{
  "ok": false,
  "status": "prepare_token_set_not_consumed",
  "error_type": "prepare_token_set_not_consumed",
  "submit_method": "button_click|keyboard_enter|enter_fallback",
  "prefer_button_submit": true,
  "submit_button_visible": true,
  "submit_button_enabled": true,
  "submit_prepare_request_observed": true,
  "submit_prepare_response_observed": true,
  "submit_message_request_observed": false,
  "submit_backend_commit_confirmed": false,
  "post_submit_user_turn_visibility_status": "user_turn_echo_not_visible",
  "submit_dom_delta_status": "dom_delta_user_turn_not_confirmed",
  "answer_text_length": 0
}
```

## Validation performed

- Python compile check:
  - `python -m py_compile promptbranch_cli.py promptbranch_service_client.py promptbranch_container_api.py promptbranch_automation/service.py promptbranch_browser_auth/client.py promptbranch_version.py`
- Focused pytest validation:
  - `tests/test_project_list_browser_client.py::test_submit_prompt_button_path_skips_slow_user_turn_dom_wait_after_running_confirmation`
  - `tests/test_project_list_browser_client.py::test_submit_prompt_uses_keyboard_enter_as_primary_dispatch`
  - `tests/test_project_list_browser_client.py::test_submit_prompt_prefer_button_overrides_keyboard_primary_when_prompt_file_policy_is_set`
  - `tests/test_project_list_browser_client.py::test_submit_failure_diagnostics_flatten_prepare_token_not_consumed`
  - `tests/test_promptbranch_cli.py::test_main_ask_combines_prompt_file_and_repeatable_attachments`
  - `tests/test_promptbranch_cli.py::test_ask_live_profile_runs_visible_operator_steps_in_retained_delete_frozen_project`
  - `tests/test_promptbranch_service_client.py::test_ask_result_posts_prefer_button_submit_form_field`
  - `tests/test_promptbranch_container_api.py::test_ask_passes_prefer_button_submit_when_requested`
  - `tests/test_promptbranch_shell_scripts.py::test_prompt_file_live_smoke_script_validates_button_first_submit_contract`
  - `tests/test_promptbranch_version.py`
- Shell syntax check:
  - `bash -n scripts/smoke-pb-ask-prompt-file.sh`

## Validation not performed

- Full release-control was not run in this environment.
- The live `pb ask --prompt-file` smoke was added but not executed against ChatGPT in this environment.
- Artifact adoption/current verification was not run in this environment.

A broader local run of `tests/test_promptbranch_cli.py` currently reaches an unrelated existing source-add test double failure where the fake service client does not implement `browser_status`. This repair does not change the source-add/source-check path.

## Scope confirmation

No normal slice or line advanced. This repair changes only prompt-file submit policy, submit-causality diagnostics, and focused validation support. It does not change CV generator code, source add/remove behavior, project deletion behavior, artifact registry design, or retry/backoff policy beyond the button-first prompt-file submit fix.
