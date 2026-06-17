# Repair v0.1.78.2.5 — Run-all verdict accuracy and live-profile auth preflight

## Problem

`v0.1.78.2.4 --run-all-tests` correctly continued after individual failures, but the final run-all result was not trustworthy enough for adoption decisions:

- `ask-live` could enter an unauthenticated/passkey-enrollment browser state before the real ask workflow ran.
- `visual-artifact-roundtrip` and `release-live` could be misclassified when nested artifact-download transport objects contained `ok: false` even though the top-level live test passed.
- The final all-tests summary did not include the `pb test full` transport steps, so the operator could not see direct/localhost full-suite status in one final GO/FIX report.

## Scope

- Add a live-profile preflight step before live ask/artifact tests in `--run-all-tests`.
- Use the authenticated `.pb_profile_local_debug` seed with a refreshed `release-live` profile-pool slot for `ask-live`, `visual-artifact-roundtrip`, and `release-live` under `--run-all-tests`.
- Skip live browser tests with structured failure rows when preflight fails, while still continuing to `import-smoke` and `artifact guard`.
- Make all-tests JSON selection use the top-level Promptbranch result, not nested JSON fragments.
- Include `full_direct` / `full_localhost` steps in the final all-tests summary.
- Add `.pb_profile_local_debug_pools/` to `.gitignore`.

## Out of scope

- Secure ChatGPT Project deletion protocol.
- Any ChatGPT Project deletion attempt.
- Project Source removal behavior changes.
- Artifact adoption/current mutation.
- v0.1.79 / k8s-game foundation work.

## Validation

Focused validation should include:

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q \
  tests/test_promptbranch_version.py \
  tests/test_cli_parser.py::test_parser_accepts_release_live_profile_pool_defaults \
  tests/test_cli_parser.py::test_parser_accepts_ask_live_profile_pool_when_requested \
  tests/test_promptbranch_shell_scripts.py::test_release_control_run_all_tests_continues_and_writes_final_report \
  tests/test_promptbranch_cli.py::test_ask_live_profile_runs_visible_operator_steps_in_retained_delete_frozen_project \
  tests/test_promptbranch_cli.py::test_visual_artifact_roundtrip_wraps_ask_and_artifact_intake \
  tests/test_promptbranch_cli.py::test_visual_artifact_roundtrip_failure_payload_waits_for_temp_project_cleanup \
  tests/test_promptbranch_cli.py::test_visual_artifact_roundtrip_explicit_conversation_url_skips_temp_project \
  tests/test_project_control_surface.py \
  tests/test_project_delete_safety.py
```

Also run compile/shell guards and Artifact Guardian before handoff.

## Expected release-control behavior

```text
./chatgpt_claudecode_workflow_release_control.sh \
  --version v0.1.78.2.5 \
  --install-from-zip ~/Downloads/chatgpt_claudecode_workflow-2_v0.1.78.2.5.zip \
  --run-all-tests \
  --skip-docker-logs \
  --prune-release-logs \
  --release-log-keep 12
```

The final report should contain at least:

```text
full_direct
full_localhost
live_profile_preflight
ask_live
visual_artifact_roundtrip
release_live
import_smoke
artifact_guard
```

and should return `GO` only when every top-level step is green.
