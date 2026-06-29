# Release v0.1.104

## Slice

Sandbox mutation verification and rollback evidence gate.

## Baseline

Accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.103.zip`.

## Scope

`v0.1.104` adds a verification-only gate for the sandbox mutation payload introduced in `v0.1.103`.

The new gate verifies:

- source payload schema is `promptbranch.loop.sandbox_file_mutation`;
- sandbox mutation succeeded;
- sandbox fixture before/after evidence differs;
- repository fixture before/after evidence remains identical;
- temporary sandbox workspace deletion is recorded as rollback/cleanup evidence;
- Project Source mutation, artifact adoption, deployment, Kubernetes mutation, and ChatGPT Project deletion remain false.

## CLI

```bash
pb loop run \
  --target examples/loop-targets/sandboxed-file-mutation-target.json \
  --read-only-execution \
  --evidence-gate \
  --execute-read-only-validation \
  --diagnose-read-only-result \
  --generate-correction-plan \
  --execute-sandbox-mutation \
  --verify-sandbox-mutation \
  --json
```

## Out of scope

- repository fixture mutation;
- promotion of sandbox changes into repository files;
- automatic correction retry;
- patch/diff artifact generation;
- Project Source mutation;
- artifact adoption;
- deployment or Kubernetes mutation;
- ChatGPT Project deletion.

## Validation

Focused validation must cover loop payload tests, CLI flag tests, control-surface validation, version surface validation, compileall, release-control shell syntax, Artifact Guardian, and artifact verification before handoff.
