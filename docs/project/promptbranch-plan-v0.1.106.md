# Promptbranch plan at v0.1.106

## Baseline authority

```text
accepted/current artifact: chatgpt_claudecode_workflow-2_v0.1.105.1.zip
accepted/current version:  v0.1.105.1
validation:                10/10 GO
adoption:                  release_adopted_and_verified
```

The repaired readiness command is accepted and location-independent. Three independent sandbox proofs produce one canonical fingerprint while retaining zero broader execution authority.

## Active slice

### v0.1.106 — Controlled correction promotion decision record

This slice records exactly one deterministic GO/NO-GO decision from the accepted readiness contract.

Operator command:

```bash
pb loop promotion-decision \
  --target examples/loop-targets/sandboxed-file-mutation-target.json \
  --runs 3 \
  --json
```

The command reruns the accepted readiness assessment and emits:

- `go` only when every mandatory evidence and safety check passes;
- `no_go` when any evidence, determinism, workspace-independence, rollback, cleanup, root-resolution, or authority condition fails.

## Mandatory evidence

GO requires all of the following:

- exact readiness schema and terminal `ready` status;
- exact readiness decision `ready_for_explicit_v0.1.106_go_no_go_decision`;
- exactly three observed and complete evidence runs;
- every readiness check true, with no failed checks or execution blockers;
- one deterministic SHA-256 fingerprint across all three runs;
- three distinct temporary workspaces;
- every evidence run complete with no failed checks;
- readiness remains assessment-only and has not already recorded a promotion decision;
- no broad or specific repository, deployment, Kubernetes, Project Source, artifact-adoption, or Project-deletion authority;
- the existing sandbox contract is reused with no new mutation operation;
- no repository mutation, deployment, Project Source mutation, artifact adoption, or Project deletion occurred.

The accepted GO fingerprint is:

```text
470e04f73c008bcd49827102f94f84e447f6f8618db69ae3272159f637959756
```

## Mandatory stop conditions

Any failed mandatory check records NO-GO. This includes:

- readiness `not_ready` or `blocked`;
- target or repository-root resolution failure;
- missing, incomplete, contradictory, or unsafe evidence;
- failed before/after hash or sandbox gate;
- validation failure or timeout;
- non-read-only validation evidence;
- repository drift;
- rollback failure;
- temporary workspace reuse or cleanup failure;
- fingerprint disagreement;
- any requested or observed broader mutation authority.

## Decision

The project decision record is:

```text
decision: GO
decision scope: controlled execution-envelope design only
next permitted slice: v0.1.107 — Controlled correction execution envelope design
```

The canonical machine-readable record is `docs/project/correction-promotion-decision-v0.1.106.json`.

## Authority boundary

GO does not enable correction execution. It grants only permission to design the deterministic execution envelope in `v0.1.107`.

Still forbidden:

- mutation of a disposable repository;
- mutation of a real repository;
- deployment or Kubernetes changes;
- Project Source mutation from the loop;
- artifact adoption from the loop;
- ChatGPT Project deletion;
- generic shell or write authority;
- automatic correction outside the existing temporary sandbox.

## Acceptance

The candidate must preserve:

- the v0.1.105.1 target-anchored readiness implementation;
- the v0.1.104 sandbox implementation and 13-gate release verifier;
- fresh full_direct and independent full_localhost;
- all ten release gates;
- current-turn readiness, visual completion, source handling, hermetic release-validation isolation, and evidence-bound adoption.
