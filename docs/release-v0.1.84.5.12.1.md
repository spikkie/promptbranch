# Release v0.1.84.5.12.1 — repair: recovered ask-live summary classification

## Type

Repair release for `v0.1.84.5.12`.

## Base release

`chatgpt_claudecode_workflow-2_v0.1.84.5.12.zip`

## Reason

The full release-control run for `v0.1.84.5.12` produced a functionally verified `ask_live` result with `status=verified_with_recovered_rate_limit`, `rate_limit_recovered=true`, all expected sentinels present, and `functional_failure_count=0`, but the all-tests summary still classified `ask_live` as failed because the summary classifier only accepted recovered rate-limit evidence when a modal-acknowledged cooldown event was present.

The live log showed recovered conversation-history `429` telemetry with cooldown waits and functional verification. This repair extends release-control recovered-rate-limit classification to accept top-level `rate_limit_recovered=true` after the existing functional-success checks pass.

## Files changed

- `chatgpt_claudecode_workflow_release_control.sh`
- `tests/test_promptbranch_shell_scripts.py`
- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `docs/release-v0.1.84.5.12.1.md`
- `docs/project/release-status.md`
- `docs/project/status.md`

## Scope boundary

No slice or line advanced. The active slice remains `v0.1.84.5.12 — Explicit new-task ask mode`.

No changes were made to:

- `pb ask --new-task` routing semantics
- composer no-fill safety
- Project Source mutation
- artifact adoption/current behavior
- Project deletion behavior

## Validation

Focused repair validation:

```bash
pytest -q \
  tests/test_promptbranch_shell_scripts.py::test_release_control_all_tests_summary_accepts_ok_false_verified_recovered_ask_live_payload \
  tests/test_promptbranch_shell_scripts.py::test_release_control_all_tests_summary_rejects_verified_recovered_ask_live_with_functional_failure

bash -n chatgpt_claudecode_workflow_release_control.sh
python3 -m compileall -q promptbranch_cli.py promptbranch_container_api.py promptbranch_browser_auth promptbranch_automation promptbranch_service_client.py
python3 promptbranch_cli.py artifact guard --zip chatgpt_claudecode_workflow-2_v0.1.84.5.12.1.zip --version v0.1.84.5.12.1 --json
```

Full release-control/adoption was not run in the assistant environment.
