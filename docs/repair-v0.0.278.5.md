# Repair v0.0.278.5 — Plain ask canonical answer renderer

Base release: `v0.0.278.4`

Repair version: `v0.0.278.5`

## Reason

`v0.0.278.4` fixed browser-profile scheduler UX, but a separate rendering defect remained in plain `pb ask` output. When the service returned a complete answer as `answer.paragraphs[]`, `pb ask --json` contained the full answer while plain `pb ask` could print an incomplete or non-canonical representation. This made Terminal A look truncated even though the service response and task recovery held the complete answer.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `promptbranch_cli.py`
- `tests/test_promptbranch_cli.py`
- `promptbranch.egg-info/PKG-INFO`
- `promptbranch.egg-info/SOURCES.txt`
- `docs/repair-v0.0.278.5.md`

## Change summary

- Added canonical answer text normalization for ask responses.
- Supports answers returned as:
  - plain string
  - `answer.text`
  - `answer.paragraphs[]`
  - list of answer fragments
- Plain `pb ask` now prints canonical full answer text.
- `pb ask --json` now includes:
  - `answer_text`
  - `answer_text_length`
  - `answer_text_sha256`
  - `answer_paragraph_count`
- If `answer` is a dictionary, JSON output also exposes `answer.text` as the canonical flattened text when absent.

## Validation performed

- `python3 -m py_compile promptbranch_cli.py promptbranch_version.py`
- `pytest -q tests/test_promptbranch_cli.py::test_plain_ask_renders_all_answer_paragraphs tests/test_promptbranch_cli.py::test_json_ask_exposes_canonical_answer_text_for_paragraphs tests/test_promptbranch_cli.py::test_main_can_ask_via_service_backend`
- `pytest -q tests/test_promptbranch_cli.py::test_main_can_ask_via_service_backend tests/test_promptbranch_cli.py::test_plain_ask_renders_all_answer_paragraphs tests/test_promptbranch_cli.py::test_json_ask_exposes_canonical_answer_text_for_paragraphs tests/test_promptbranch_service_client.py tests/test_promptbranch_timeout_classification.py tests/test_promptbranch_container_api.py tests/test_promptbranch_automation_service.py tests/test_cli_parser.py tests/test_compose_timeout_policy.py` — 116 passed.
- `pytest -q tests/test_chatgpt_container_api.py tests/test_promptbranch_container_api.py tests/test_cli_parser.py tests/test_compose_timeout_policy.py` — 73 passed.
- ZIP reopened and verified for direct repository-root layout and hygiene.

## Scope control

This repair does not advance a slice, open a new line, introduce an async queue, or change browser scheduling semantics. It preserves the `v0.0.278.4` single-owner browser profile monitor behavior and only repairs canonical answer rendering/output.
