# Release v0.1.103

## Slice

`v0.1.103 — First controlled file mutation in sandboxed fixture only`

## Baseline

Accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.102.zip`.

## Scope

- Add the first controlled file mutation path to the loop runner.
- Require prior read-only command execution, diagnosis, and correction-plan evidence.
- Permit mutation only on a copied fixture inside a temporary sandbox workspace.
- Keep the repository fixture unchanged and record before/after hashes for both the repository fixture and sandbox copy.
- Add CLI flag `--execute-sandbox-mutation` gated behind `--generate-correction-plan`.
- Add sandbox mutation target fixture under `examples/loop-targets/` and source fixture under `examples/loop-sandbox/`.

## Out of scope

- Repository file mutation.
- Sandbox mutation verification/rollback gates beyond before/after evidence.
- Automatic command retry outside the sandbox.
- Patch/diff artifact generation.
- Deployment or Kubernetes mutation.
- Project Source mutation.
- Artifact adoption behavior change.
- ChatGPT Project deletion.

## Validation

Focused validation for loop/CLI/control-surface/artifact behavior is required before handoff. Full release-control/adoption remains the operator acceptance gate.
