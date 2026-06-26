# Release v0.1.93 — MVP-1 planned-action walkthrough

## Baseline

Built from accepted/current `chatgpt_claudecode_workflow-2_v0.1.92.zip`.

`v0.1.92` opened MVP-1 with a state-only loop walkthrough. `v0.1.93` keeps the loop side-effect free but advances the operator-visible plan model by showing the planned action and validation gate for each state.

## Scope

Normal MVP-1 feature slice.

In scope:

- Add `pb loop run --planned-actions` text output.
- Add `pb loop run --planned-actions --json` structured output.
- Add deterministic `planned_action`, `validation_gate`, and `execution_status=not_executed_dry_run` metadata for loop events.
- Preserve default verbose dry-run output and `--state-only` behavior.
- Preserve no-action/no-mutation/no-deployment/no-adoption semantics.

Out of scope:

- Executing commands.
- Mutating repository files.
- Running validation commands from the target.
- Kubernetes, Docker, Helm, or cluster mutation.
- ChatGPT Project Source mutation.
- Artifact adoption/current changes from loop commands.
- ChatGPT Project deletion.

## Operator command

```bash
pb loop run --target examples/loop-targets/static-game-dry-run-target.json --planned-actions
```

Text output prints one line per state:

```text
INTAKE | action=load target definition and create loop context | gate=target JSON parsed and target_id/goal are available | next=REQUIREMENTS_CHECK
...
SOLVED | action=stop the loop because the dry-run plan reaches its terminal success state | gate=final state is recorded without artifact adoption | next=none
```

JSON output:

```bash
pb loop run --target examples/loop-targets/static-game-dry-run-target.json --planned-actions --json
```

emits `mode=planned_actions` with an `actions[]` list and no raw `events` list.

## Safety contract

`--planned-actions` is presentation-only. It explains what a future execution loop would do next, but it does not execute the action. All safety flags remain false:

- `commands_executed=false`
- `deployment_performed=false`
- `kubernetes_mutation_performed=false`
- `project_source_mutation_performed=false`
- `artifact_adoption_performed=false`
- `chatgpt_project_deletion_performed=false`

## Validation

Focused validation for the candidate must cover:

- loop target validation
- default dry-run loop run
- `--state-only` compatibility
- `--planned-actions` text output
- `--planned-actions --json` output
- mutual exclusion between `--state-only` and `--planned-actions`
- version consistency
- project control-surface validation
- compileall
- release-control shell syntax
- Artifact Guardian
- artifact verify

Full release-control/adoption is required before this candidate is accepted/current.
