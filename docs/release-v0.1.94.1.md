# Release candidate v0.1.94.1 — Project Source capacity-prune identity guard

`v0.1.94.1` is a repair-only candidate for the intended `v0.1.94` first controlled read-only execution step.

## Summary

The candidate preserves the `v0.1.94` loop capability:

```bash
pb loop run --target examples/loop-targets/static-game-dry-run-target.json --read-only-execution
pb loop run --target examples/loop-targets/static-game-dry-run-target.json --read-only-execution --json
```

The loop remains read-only. It inspects declared path scopes and validation command declarations but executes no commands and performs no mutation.

The repair hardens Project Source capacity pruning. If the exact remove of the selected prune target reports source-row identity drift or collateral removal, Promptbranch now stops immediately, returns `operator_review_required=true`, records `capacity_prune_retry_suppressed=true`, and does not retry with a looser lookup.

## Safety boundaries

```text
commands_executed=false
side_effects_performed=false
kubernetes_mutation_performed=false
project_source_mutation_performed=false
artifact_adoption_performed=false
chatgpt_project_deletion_performed=false
```

## Acceptance requirement

This ZIP is not accepted/current until full release-control passes and `pb artifact current --json` proves runtime, state artifact/source, registry current, and consistency alignment.
