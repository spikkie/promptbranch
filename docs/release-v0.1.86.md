# Release v0.1.86 — K8s-game orchestration plan reconciliation

## Baseline

```text
chatgpt_claudecode_workflow-2_v0.1.85.zip
```

## Slice

`v0.1.86` reconciles the Kubernetes game orchestration plan to the accepted/current Promptbranch baseline before implementation starts.

## Changes

- Updated project control-surface docs for the `v0.1.85` accepted baseline and `v0.1.86` reconciliation slice.
- Refreshed orchestration current status from stale `v0.1.79` wording to the accepted `v0.1.85` baseline.
- Clarified that k8s-game remains a controlled lifecycle test vehicle, not the product.
- Defined the next allowed game implementation path as static-first and repository-local only.
- Kept Kubernetes mutation blocked until a later explicit dry-run/deploy evidence gate exists.

## Out of scope

```text
no game implementation
no Docker image build/publish
no Kubernetes apply
no Helm release
no cluster mutation
no Project Source mutation
no artifact adoption/current behavior change
no accepted-event ledger write
no ChatGPT Project deletion behavior change
```

## Validation

Focused validation should include:

```bash
python3 -m pytest -q tests/test_project_control_surface.py tests/orchestration/test_orchestration_examples.py tests/test_promptbranch_version.py
python3 -m compileall -q promptbranch_cli.py promptbranch_state.py promptbranch_orchestration.py
python3 promptbranch_cli.py artifact guard --zip chatgpt_claudecode_workflow-2_v0.1.86.zip --version v0.1.86 --json
python3 promptbranch_cli.py artifact verify chatgpt_claudecode_workflow-2_v0.1.86.zip --json
```

Full release-control/adoption remains required before calling this accepted/current.
