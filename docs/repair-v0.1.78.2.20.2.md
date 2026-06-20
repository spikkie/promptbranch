# Repair note — v0.1.78.2.20.2

## Scope

- Base release: `v0.1.78.2.20.1`
- Repair version: `v0.1.78.2.20.2`
- Release type: repair-on-repair
- Slice advancement: none

## Reason

The tiny `pb ask --prompt-file` smoke passed after the button-first submit repairs, but the full CV RAG prompt package still failed with `submit_causality_not_confirmed`. The large prompt was inserted into the composer and dispatched by button click, but ChatGPT rendered it as a large pasted/document-style user turn. Promptbranch could not prove the committed current user turn from exact markers or DOM delta, so it correctly refused to return a potentially stale answer.

The operator updated the change request to focus on automated prompt-file attachment mode for large prompt packages. This repair follows that direction instead of weakening submit dispatch causality.

## Changes

- `promptbranch_cli.py`
  - Adds `--prompt-file-mode {auto,inline,attach}` for `pb ask`.
  - Adds `--prompt-file-attach-threshold-bytes` for `pb ask`.
  - Defaults `--prompt-file-mode` to `auto`.
  - Automatically attaches prompt files whose UTF-8 size is at least 12,000 bytes.
  - Keeps smaller prompt files inline for backwards compatibility.
  - Emits `prompt_file_transport` evidence in the structured ask result.
- `scripts/smoke-pb-ask-large-prompt-file.sh`
  - Adds a focused large prompt-file smoke that validates attachment transport, button-first submit, non-empty answer text, and the `CV_MARKDOWN` / `EVIDENCE_SIDECAR_JSON` contract markers.
- `tests/test_promptbranch_cli.py`
  - Adds regression coverage for auto-attaching large prompt files.
  - Adds regression coverage for forcing large prompt files inline.

## Non-changes

- No CV generator code changed.
- No Project Source add/remove behavior changed.
- No artifact registry behavior changed.
- No project deletion behavior changed.
- No normal slice advanced.
- The tiny prompt-file smoke and button-first submit policy are preserved.

## Validation performed

Focused local validation was performed for parser/transport behavior, version consistency, project control surface, compile checks, shell syntax, ZIP integrity, and ZIP hygiene. Full release-control, live large prompt smoke, and adoption/current verification must still be run by the operator.
