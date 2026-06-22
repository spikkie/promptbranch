# Repair v0.1.84.5 — visual artifact reply-envelope hardening

## Base

Repair candidate on top of focused `v0.1.84.4`. Accepted/current remains `v0.1.79` until full validation and adoption/current evidence exists.

## Reason

The v0.1.84.4 full all-tests/adoption gate failed only in `visual_artifact_roundtrip`. The failing attempts produced near-complete replies, but candidate selection never ran because the reply parser rejected invalid JSON: one answer included raw nested quotes in a validation string, and another answer had a balanced JSON object followed by a truncated end-marker fragment.

## Changes

- Hardened the visual artifact prompt to request simple validation strings and avoid JSON arrays, raw double quotes, and Markdown links inside string values.
- Added parser recovery for the specific safe case where a balanced JSON object is followed only by a truncated `END_PROMPTBRANCH_REPLY_JSON` marker fragment.
- Kept strict failure for malformed JSON with raw nested quotes, missing commas, or non-marker trailing prose.
- Added focused regression coverage for the truncated-marker recovery, raw-quote rejection, non-marker trailing text rejection, and visual prompt hardening.

## Out of scope

No project deletion, ledger creation, ledger append, `accept-event --write`, Project Source mutation, artifact adoption/current mutation, deployment, or model execution behavior changed.

## Validation

Focused validation completed for this repair candidate:

- `python3 -m pytest -q tests/test_promptbranch_ask_protocol.py tests/test_promptbranch_cli.py::test_visual_artifact_roundtrip_prompt_uses_simple_validation_strings tests/test_promptbranch_version.py tests/test_project_control_surface.py` passed (`26 passed`).
- `python3 -m pytest -q tests/test_promptbranch_cli.py -k 'visual_artifact_roundtrip or artifact_intake_from_parsed_answer or ask_protocol'` passed (`16 passed, 288 deselected`).
- `python3 -m pytest -q tests/test_promptbranch_version.py tests/test_project_control_surface.py` passed (`8 passed`).
- `python3 -m compileall -q .` passed.
- `bash -n chatgpt_claudecode_workflow_release_control.sh` passed.
- `python3 promptbranch_cli.py orchestration validate-ledger --json` passed.
- Artifact Guardian passed for `chatgpt_claudecode_workflow-2_v0.1.84.5.zip`.

Full all-tests/adoption remain pending.
