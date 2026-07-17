# Release v0.1.104

## Slice

`v0.1.104 — Sandbox mutation verification and rollback evidence gate`

## Baseline

Accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.103.10.116.zip`.

## Scope

- Store the Promptbranch roadmap and current-state handoff in `docs/project/promptbranch-plan-v0.1.104.md`.
- Require exact expected-before and expected-after SHA-256 evidence for the copied fixture.
- Permit only one literal repo-relative fixture under `examples/loop-sandbox/` and one `replace_contents` operation.
- Run exactly one allowlisted `python3 -m json.tool <fixture>` command inside the temporary workspace.
- Require the validation command to pass and leave the sandbox fixture unchanged.
- Restore the original bytes and require the rollback snapshot to equal the before snapshot.
- Require the repository fixture to remain unchanged and the temporary workspace to be deleted.
- Emit `sandbox_mutation_verified_and_rolled_back` only when every gate passes.
- Fail closed and stop for operator review on any missing or contradictory evidence.

## Out of scope

- Repository file mutation.
- Automatic command retry.
- Patch or diff generation.
- Deployment or Kubernetes mutation.
- Project Source mutation.
- Artifact adoption behavior changes.
- ChatGPT Project deletion.
- Promotion beyond sandbox fixtures.

## Primary command

```bash
pb loop run \
  --target examples/loop-targets/sandboxed-file-mutation-target.json \
  --read-only-execution \
  --evidence-gate \
  --execute-read-only-validation \
  --diagnose-read-only-result \
  --generate-correction-plan \
  --execute-sandbox-mutation \
  --json
```

## Expected terminal result

```text
schema:   promptbranch.loop.sandbox_mutation_verification
status:   sandbox_mutation_verified_and_rolled_back
decision: stop_after_verified_sandbox_rollback_evidence
```

## Next slice after acceptance

`v0.1.105 — Sandbox correction promotion readiness check`.
