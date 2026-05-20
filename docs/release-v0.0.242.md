# Release v0.0.242

## Scope

Artifact Intake MVP operator cockpit.

## Base

Built from `chatgpt_claudecode_workflow_v0.0.241.2.zip`.

## Changes

- Added `pb artifact mvp-status` as a read-only MVP status command.
- Aggregates current artifact state, candidate inventory summary, latest protocol-artifact precondition, candidate-next recommendation, and MVP completion proof.
- Exposes common inspection/finalization command hints for the operator.

## Non-goals

- No new source upload behavior.
- No new candidate adoption behavior.
- No automatic artifact intake beyond existing explicit `candidate-run` behavior.
- No protocol schema change.

## Validation

Focused parser/CLI tests, py_compile, version smoke, ZIP hygiene, and ZIP CRC verification.
