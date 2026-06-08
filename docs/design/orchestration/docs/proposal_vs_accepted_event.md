# Proposal vs Accepted Event

## Purpose

This document defines the trust boundary for JSON Orchestration State MVP.

The central rule is:

```text
ChatGPT may propose.
Promptbranch decides whether the proposal is admissible.
```

## ChatGPT proposal

A proposal is untrusted model output.

It may contain:

```text
- stage classification
- reasoning summary
- risks
- proposed transition
- required agents/gates
- next action recommendation
```

A proposal must not be treated as workflow state until Promptbranch validates it.

## Promptbranch accepted event

An accepted event is trusted workflow state created after deterministic validation.

Promptbranch must validate:

```text
- schema identity
- schema version
- request_id / correlation_id
- current state
- proposed transition
- execution authority boundary
- required evidence/gates
- no forbidden capability request
```

## Evidence

Evidence is deterministic output from tools, tests, release checks, or deployment checks.

Examples:

```text
- pytest result
- ZIP hygiene result
- artifact verify result
- kubectl rollout status
- HTTP smoke result
```

ChatGPT may summarize evidence, but Promptbranch decides whether evidence passes.

## Artifact

Release ZIPs remain governed by the Final Artifact Intake MVP.

Planning decisions do not replace artifact verification.

```text
Planning decisions -> orchestration event store
Release ZIPs       -> artifact intake
Deployment results -> evidence records
```
