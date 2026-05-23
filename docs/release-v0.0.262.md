# Release v0.0.262

## Type
Normal development release built from accepted baseline `chatgpt_claudecode_workflow_v0.0.261.zip`.

## Scope
Harden Promptbranch protocol answer selection after diagnostic chatter.

## Changes
- Added explicit `pb task answer parse --message-id` and `--message-index` selectors for parity with `pb artifact intake`.
- Added global `--answer-id` resolution for `pb task answer parse` when no user-message selector is provided.
- Added structured `answer_selection` reporting to `pb task answer parse` output.
- Preserved existing scoped behavior when a user message selector is supplied.

## Reason
The v0.0.259/v0.0.260 artifact-intake proof showed that operators can discover a protocol assistant answer id from task-message JSON but still fail parsing because `--answer-id` was scoped to the latest user message. This release removes that ambiguity for the common unique-answer-id case.

## Validation
- `python3 -m compileall -q .`
- Focused parser tests for explicit message selectors.
- Focused CLI tests for global answer-id resolution and scoped message/answer selection.
- Extracted ZIP smoke for `promptbranch 0.0.262` and parse-help selector visibility.

## Not performed
- Project Source mutation
- Artifact adoption
- Git commit
- Git push
