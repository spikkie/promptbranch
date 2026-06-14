# Release v0.1.77

## Type

```text
normal candidate
```

## Baseline

```text
chatgpt_claudecode_workflow-2_v0.1.76.zip
```

## Slice

```text
Repo-loop compatibility hardening and operator migration guardrails
```

## Goal

Make remaining artifact-current compatibility behavior explicit after the KISS repo-loop transition. Normal operator/release paths consume repo-loop entries for one repo and many repos. Legacy top-level parsing remains only as an explicit compatibility fallback for older logs and non-joined payloads.

## Scope

In scope:

- update project control surface to record v0.1.76 as accepted/current;
- strengthen normalized artifact-current section selection in `promptbranch_cli.py`;
- update release/dev/lifecycle evidence helpers to consume selected repo-loop sections;
- update parallel ask baseline safety to read repo-loop artifact-current payloads;
- add focused tests for repo-loop precedence and explicit legacy fallback behavior;
- add a migration note for operator scripts that still parse old top-level fields.

Out of scope:

- artifact registry storage format changes;
- adoption semantics changes;
- Project Source upload behavior changes;
- dependency solving between repos;
- automatic multi-repo adoption;
- release-set orchestration;
- browser automation changes;
- Docker/deployment behavior.

## Compatibility note

Joined projects use this normal shape:

```text
payload.repos[repo_id].state
payload.repos[repo_id].registry_current
payload.repos[repo_id].baseline_roles
payload.repos[repo_id].runtime
payload.repos[repo_id].consistency
```

Legacy top-level fields are compatibility-only:

```text
payload.state
payload.registry_current
payload.baseline_roles
payload.runtime
payload.consistency
```

## Validation intent

Required focused validation:

```text
pytest artifact-current/repo-loop compatibility tests
pytest parallel ask baseline safety tests
pytest project control surface tests
pytest version tests
bash syntax checks
compileall
clean extraction validation
```

## Acceptance rule

This release is a candidate until release-control and adoption/current evidence prove runtime, state artifact, state source, registry current, and consistency alignment.
