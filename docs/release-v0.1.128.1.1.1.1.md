# v0.1.128.1.1.1.1 — Fresh assistant-chain continuity repair

## Baseline

Authoritative adopted/current baseline remains `v0.1.128.1.1` with artifact SHA-256 `89fe16e498b3035f94db5375c7ef9ee924a9d82d15ce5790ef765658e0db6328`. Immutable predecessor candidate `v0.1.128.1.1.1` proved the post-adoption projection-completeness construction repair but could not reach `TESTED_GREEN`: both full lifecycle and focused browser `ask_question` reproduced a service deadline after successful UI submission and generation.

## Live defect reproduced

The real Patchright/Chrome frontend submitted `INTEGRATION_OK` successfully. The new assistant turn first appeared as `Thinking`, then partial text, then completed as `INTEGRATION_OK`. ChatGPT became idle, but visible assistant virtualization reduced the count below the baseline. The freshness predicate accepted transient baseline-different text, then rejected the completed deterministic answer solely because it became byte-identical to the pre-submit baseline, freezing stable-poll/completion progress until the service deadline.

## Repair scope

- Preserve the `.1.1.1` projection-completeness repair unchanged.
- Latch a post-submit assistant chain only after confirmed submit + observed generation + independent fresh-response evidence.
- Continue treating subsequent non-empty latest-assistant text at the same visible assistant count as the same causally fresh chain.
- Permit the completed fresh chain to equal the historical baseline text.
- Preserve fail-closed rejection when baseline-identical text appears without the causal freshness latch.
- Add the exact `Thinking → partial → baseline-identical final` regression.

## Non-goals

No new lifecycle state, no timeout increase, no stale-response shortcut, no backend/API-only acceptance path, no compatibility shim, and no external-application scope. `v0.1.129` remains blocked until this repair closes live.
