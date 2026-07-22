# Release v0.1.105

## Slice

`v0.1.105 — Sandbox correction promotion readiness check`

## Baseline

Accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.104.5.zip`.

## Scope

- Add `pb loop promotion-readiness`.
- Run the existing sandbox-only correction proof three independent times by default.
- Require complete exact evidence from every run.
- Canonicalize deterministic evidence and compare SHA-256 fingerprints.
- Require distinct temporary workspace identities.
- Emit exactly `ready`, `not_ready`, or `blocked`.
- Keep every existing sandbox mutation, validation, rollback, cleanup, and release gate unchanged.
- Preserve fresh `full_direct`, independent `full_localhost`, all ten release gates, and evidence-bound adoption.

## Authority boundary

Even `ready` grants no broader mutation authority and records no promotion decision. Only `v0.1.106` may record an explicit GO/NO-GO decision.

## Primary command

```bash
pb loop promotion-readiness \
  --target examples/loop-targets/sandboxed-file-mutation-target.json \
  --runs 3 \
  --json
```

## Expected candidate assessment

```text
schema:   promptbranch.loop.sandbox_correction_promotion_readiness
status:   ready
decision: ready_for_explicit_v0.1.106_go_no_go_decision
observed_run_count: 3
unique_fingerprint_count: 1
broader_mutation_authority_granted: false
promotion_decision_recorded: false
```

## Out of scope

- Recording a promotion GO/NO-GO decision.
- Repository correction.
- Deployment or Kubernetes mutation.
- Project Source mutation from the loop.
- Artifact adoption from the loop.
- ChatGPT Project deletion.
- New mutation operations or broader shell execution.

## Next slice after acceptance

`v0.1.106 — Controlled correction promotion decision record`.
