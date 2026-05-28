# Release v0.0.278.40

## Scope

Small performance-only follow-up to v0.0.278.39.

## Changes

- Adds a fast latest-turn visible answer promotion path before the full post-submit user-turn visibility probe.
- Accepts only parseable JSON that contains the exact current request marker/sentinel.
- Rejects prompt echoes before parsing as answer candidates.
- Falls back to the v0.0.278.39 post-submit visibility behavior when the fast path does not find a fresh answer.

## Validation

- `python3 -m compileall -q .`
- focused pytest suites for browser client, service client, container API, compose timeout policy, CLI parser, ChatGPT container API, and Promptbranch CLI.

## Operator note

This release intentionally does not change submit dispatch. If speed remains poor after v0.0.278.40, the next narrow candidate is making the successful trusted-refill + Enter path primary.
