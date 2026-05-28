# Repair v0.0.278.7 — Submit/Turn-Observation Latency Repair

## Base release

`v0.0.278.6`

## Repair version

`v0.0.278.7`

## Reason

`v0.0.278.6` made ask latency visible but still showed worst-case delays dominated by submit and user-turn observation:

- `submit_wait_seconds` could exceed 200 seconds.
- `submit_to_turn_visible_seconds` could exceed 120 seconds.
- The browser UI could already be running or complete while Promptbranch still waited for slow user-turn DOM evidence.

The intended repair is to confirm submit earlier from stronger running-state signals.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `docker-compose.chatgpt-service.yml`
- `promptbranch_browser_auth/client.py`
- `tests/test_project_list_browser_client.py`
- `tests/test_cli_parser.py`
- `tests/test_chatgpt_container_api.py`
- `tests/test_compose_timeout_policy.py`
- `tests/test_promptbranch_cli.py`
- `tests/test_promptbranch_container_api.py`
- `docs/repair-v0.0.278.7.md`

## Implementation notes

- Added `_wait_for_submit_confirmation()`.
- Added `_capture_submit_confirmation_state()`.
- Added cheap assistant-turn counting without text extraction.
- Treat submit as confirmed when any of these signals appears:
  - stop button visible;
  - assistant turn count increases;
  - current URL is a conversation URL;
  - composer is in a running/stop-button state.
- Button-submit and Enter-fallback paths no longer wait for slow user-turn DOM materialization after submit confirmation.
- `dom_user_turn_evidence` remains present but is marked `user_turn_dom_evidence_skipped` when submit was confirmed by running/URL signals.
- Ask phase timings now include:
  - `submit_confirmation_seconds`;
  - `submit_confirmed`;
  - `submit_confirmed_by`;
  - `enter_fallback_press_seconds`;
  - `user_turn_dom_evidence_status`.

## Validation performed

Focused validation:

```bash
pytest -q \
  tests/test_cli_parser.py \
  tests/test_promptbranch_service_client.py \
  tests/test_promptbranch_timeout_classification.py \
  tests/test_promptbranch_automation_service.py \
  tests/test_promptbranch_container_api.py \
  tests/test_project_list_browser_client.py \
  tests/test_response_completion.py \
  tests/test_chatgpt_container_api.py \
  tests/test_compose_timeout_policy.py \
  tests/test_promptbranch_cli.py::test_main_version_subcommand_outputs_release \
  tests/test_promptbranch_cli.py::test_phase1_doctor_reports_state_without_mutating \
  tests/test_promptbranch_cli.py::test_release_doctor_reports_runtime_source_mismatch_read_only \
  tests/test_promptbranch_cli.py::test_release_doctor_artifact_zip_hardening_reports_candidate_phase \
  tests/test_promptbranch_cli.py::test_release_doctor_blocks_runtime_version_file_mismatch \
  tests/test_promptbranch_cli.py::test_src_add_promotes_browser_profile_busy_to_top_level_payload \
  tests/test_promptbranch_cli.py::test_browser_status_command_uses_service_client
```

Result:

```text
181 passed
```

Additional validation:

```bash
python3 -m py_compile $(find . -name '*.py' -not -path './.venv/*' -not -path './build/*' -not -path './dist/*')
```

## Slice/line advancement

No slice, line, MVP scope, or planned feature scope was advanced. This is a repair-only release for submit confirmation latency and observability defects in the intended `v0.0.278.6` behavior.
