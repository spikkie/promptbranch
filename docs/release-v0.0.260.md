# Release v0.0.260

## Scope

Builds on accepted `chatgpt_claudecode_workflow_v0.0.259.zip` after the strict real-candidate MVP path passed.

This release hardens operator UX around answer selection and candidate-intake reporting.

## Changes

- Added `.gitignore` coverage for Promptbranch task transcript/debug exports:
  - `*.task.show.json`
- Added explicit artifact-intake protocol answer selection:
  - `pb artifact intake --from-last-answer --message-id <id-or-index> --answer-id <id-or-prefix> ...`
  - `--message-index` and `--answer-index` are also supported.
- `pb artifact intake` now promotes a valid explicitly selected task answer into `.pb_profile/ask_protocol_runs/` before manual import/verification/migration.
- Artifact-intake JSON output now reports selected protocol identity fields:
  - `selected_request_id`
  - `selected_message_id`
  - `selected_answer_id`
  - `selected_protocol_reply`
- Migrated candidate registry entries now preserve the selected protocol reply identity.
- Candidate status/run/MVP-completion reporting now surfaces selected request/message/answer identity when a candidate carries it.

## Validation

- `python3 -m compileall -q .`
- `pytest -q tests/test_cli_parser.py tests/test_promptbranch_cli.py`
- Extracted runtime smoke:
  - `promptbranch 0.0.260`
  - `pb artifact intake --help` shows explicit message/answer selector options.

## Boundaries

No automatic browser-context download was added.
No Project Source mutation, Git commit, or Git push behavior was changed.
Strict real-candidate gating remains unchanged.
