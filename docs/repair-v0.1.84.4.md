# Repair v0.1.84.4 — ChatGPT project-name length cap for generated test projects

## Base

`v0.1.84.3` focused repair candidate.

Accepted/current baseline remains `chatgpt_claudecode_workflow-2_v0.1.79.zip` until a later promotion/adoption gate provides current-state evidence.

## Reason

ChatGPT Project names are limited to 50 characters. The fresh-project-per-run repair introduced long generated names such as release-control names containing version, timestamp, and PID, and live-test names containing long profile prefixes plus operator run IDs. Operators can work around this with a short `--run-id`, but default generated names must be safe without operator intervention.

## Scope

- Cap generated ChatGPT test Project names at 50 characters.
- Preserve run-scoped uniqueness by appending a stable short hash when truncation is needed.
- Apply the cap to release-control generated project names.
- Apply the cap to `pb test ask-live`, `pb test visual-artifact-roundtrip`, and `pb test release-live` generated names.
- Apply the cap to the full integration test default generated name path.
- Fail fast if `PROMPTBRANCH_RELEASE_TEST_PROJECT_NAME` explicitly provides a value longer than 50 characters.

## Out of scope

- Re-enabling project deletion.
- Changing existing explicit `--project-name` semantics.
- Ledger writes or orchestration authority changes.
- Project Source behavior changes.
- Artifact adoption/current mutation.
- Deployment or model execution.

## Validation

Focused tests cover bounded generated live-test names and release-control generated-name policy. Existing ask-live unique-project behavior remains covered.
