# Promptbranch plan at v0.1.104

## Product direction

Promptbranch is a deterministic local control plane around ChatGPT Projects. The product flow is:

```text
Intent
  -> Contract
  -> Context
  -> Execution
  -> Evidence
  -> Adoption
  -> Ownership / next slice
```

The controlled problem-solving loop is:

```text
target
  -> understand
  -> plan
  -> act safely
  -> verify
  -> diagnose
  -> correct
  -> retest
  -> stop, adopt, or deploy only when explicitly allowed
```

ChatGPT may propose or produce a candidate. Promptbranch owns authoritative state, execution boundaries, evidence, validation, mutation authority, adoption, and continuation from the accepted baseline.

## Fixed architecture invariants

- Artifact-first baseline continuity.
- The project control surface is authoritative over conversation memory.
- Exactly one normal slice is active.
- Repair releases do not advance normal scope.
- Every mutation requires explicit identity, bounded authority, and evidence.
- Ambiguous or incomplete evidence fails closed.
- Project Source mutation and artifact adoption remain separate explicit release-lifecycle operations.
- Browser automation and live validation stay all-in-Docker.
- ChatGPT Project deletion remains frozen.
- Policies and paths remain repository-relative.

## MVP progression

### MVP-0 — release and control-plane foundation

Completed capabilities include workspace/task/artifact state separation, structured Ask/Reply envelopes, candidate ZIP intake, Artifact Guardian, Docker profile handling, project/repository identity, project-scoped artifact registries, direct and localhost validation, live ChatGPT checks, evidence-bound adoption, and final accepted/current verification.

### MVP-1 — controlled problem-solving loop

Completed slices:

| Slice | Capability |
|---|---|
| v0.1.92 | State-only loop walkthrough |
| v0.1.93 | Planned-action walkthrough |
| v0.1.94.x | Controlled read-only execution foundations |
| v0.1.95 | Compact execution-preflight evidence |
| v0.1.100 | One allowlisted read-only validation command |
| v0.1.101 | Passed/blocked/failed diagnosis |
| v0.1.102 | Non-mutating correction-plan generation |
| v0.1.103 | First mutation against a copied temporary fixture only |

The long `v0.1.103.10.x` repair line hardened the surrounding release path: Docker profiles, live completion, Project Source upload identity, overwrite, capacity, project/repository identity, evidence-bound adoption, and assigned-source-aware final verification.

## Accepted/current state

```text
accepted/current: chatgpt_claudecode_workflow-2_v0.1.103.10.116.zip
validation:        9/9 GO
adoption:          completed
final verification: release_adopted_and_verified
```

Operationally proven:

- canonical release ZIP import and installation;
- profile and authoritative-state preservation;
- exact project and repository identity;
- requested versus backend-assigned Project Source identity;
- processed-file and Library metadata ID capture;
- upload-new/verify/delete-old replacement;
- singleton source-family enforcement;
- independent direct and localhost full transports;
- live Ask/Reply and downloadable-artifact validation;
- Artifact Guardian;
- evidence-bound adoption;
- runtime/state/registry current-state consistency.

Still forbidden:

- real repository correction from the loop;
- unrestricted shell execution;
- deployment or Kubernetes mutation;
- Project Source mutation from the correction loop;
- artifact adoption from the correction loop;
- automatic promotion from assistant prose;
- ChatGPT Project deletion.

## Active slice — v0.1.104

### Sandbox mutation verification and rollback evidence gate

The existing `v0.1.103` path copied one explicit fixture into a temporary sandbox and mutated only that copy. It recorded before/after evidence, but did not prove the declared result, run validation inside the sandbox, or prove rollback.

`v0.1.104` closes exactly those gaps.

Required success sequence:

```text
validate correction-plan evidence
  -> validate literal allowlisted fixture path
  -> prove repository before hash
  -> copy fixture to temporary workspace
  -> apply one bounded replace_contents mutation
  -> prove exact declared after hash and contents
  -> run one exact allowlisted read-only validation command in the sandbox
  -> prove validation did not mutate the fixture
  -> restore the exact before snapshot
  -> prove rollback equality
  -> prove repository fixture unchanged
  -> delete the temporary workspace
  -> stop
```

Mandatory stop conditions include missing hashes, non-allowlisted paths or operations, incorrect after evidence, validation failure or timeout, validation-side mutation, repository drift, rollback failure, and workspace-cleanup failure.

Out of scope remains repository mutation, command retries, patch generation, deployment, Kubernetes changes, Project Source changes, artifact adoption, and Project deletion.

## Defined next slices

### v0.1.105 — Sandbox correction promotion readiness check

Assess whether the accumulated sandbox evidence is deterministic and complete. Produce `ready`, `not_ready`, or `blocked`; do not grant broader mutation authority.

### v0.1.106 — Controlled correction promotion decision record

Record an explicit GO/NO-GO decision on whether correction workflows may move beyond disposable sandbox fixtures. Define mandatory evidence and stop conditions.

### v0.1.107 — Controlled correction execution-envelope design

Define a future deterministic envelope containing allowed target, allowed files, allowed operation, required pre-state, required post-state, validation, rollback, limits, timeout, evidence bundle, and promotion authority. Do not enable repository-wide mutation in this slice.

## Future work is not approved yet

Any later disposable-repository correction, real-repository correction, release generation, or adoption work requires the explicit `v0.1.106` decision. The model never receives generic write authority; a deterministic execution envelope accepts or rejects a bounded correction intent.
