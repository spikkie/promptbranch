# Release v0.0.278.41

## Scope

Small submit-dispatch speed release built from `chatgpt_claudecode_workflow_v0.0.278.40.zip`.

## Change

Promotes the previously successful trusted-refill + Enter retry variant to the primary keyboard submit path.
The old raw Enter primary path remains available as fallback when trusted-refill + Enter does not produce a confirmed marker-bound submit.

## Preserved behavior

- No answer-extraction changes from v0.0.278.40.
- Exact current marker/sentinel freshness gates remain required.
- Prompt echoes and stale sentinels remain rejected.
- Existing raw Enter and retry diagnostics remain available as fallback evidence.

## Validation

- `python3 -m compileall -q .`
- Focused pytest suite covering browser client, service client, container API, compose policy, CLI parser, ChatGPT container API, and Promptbranch CLI.
- Clean extracted ZIP validation.
