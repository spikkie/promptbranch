# ADR-0002 — ChatGPT Proposal vs Promptbranch Accepted Event

## Status

Accepted.

## Decision

A ChatGPT proposal is untrusted until Promptbranch validates it and records an accepted event.

## Consequences

Automation must not use prose as operational truth. JSON is still untrusted until schema, policy, and state transition checks pass.
