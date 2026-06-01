# ADR-0003 — ChatGPT-Only LLM Provider

## Status

Accepted for v0.1.1 scope.

## Decision

Use ChatGPT as the only critical-path LLM provider for orchestration/grilling proposals.

## Reason

The MVP needs reliable structured proposal generation while Promptbranch remains validation authority. ChatGPT is the strongest available provider for this role in the current workflow.

## Consequences

No local LLM is required for the v0.1.1 validator. Provider policy is simpler and easier to test.
