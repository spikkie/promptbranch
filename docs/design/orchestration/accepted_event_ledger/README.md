# Accepted-event ledger scaffold

This directory defines the future append-only accepted-event ledger surface for Promptbranch orchestration.

## Ledger file

```text
accepted_events.jsonl
```

The ledger file is intentionally not created by the v0.1.83 slice. This slice is read-only and only validates that the contract location and record schema are present.

## Contract

Future writes must append one JSON object per line. They must not rewrite existing records, mutate Project Sources, adopt artifacts, deploy workloads, or execute model-proposed actions.

Every future ledger append must be preceded by:

1. successful accepted-event validation;
2. accepted/current baseline proof;
3. explicit operator request for a write-capable command;
4. repo-local append target validation;
5. no side effects beyond the append-only ledger record.

## Current authority

```text
write_command_available=false
accept_event_write_supported=false
accepted_state_written=false
runtime_state_mutation_allowed=false
source_mutation_allowed=false
artifact_adoption_allowed=false
deployment_allowed=false
model_may_execute=false
```
