# Release v0.1.92 — MVP-1 state-only loop walkthrough

## Baseline

```text
chatgpt_claudecode_workflow-2_v0.1.91.10.zip
```

`v0.1.92` is the first normal MVP-1 slice after the accepted/current `v0.1.91.10` release-control foundation.

## Slice

MVP-1 starts with the smallest executable proof of the automatic plan loop: Promptbranch walks a target through the complete planned loop state machine and prints only the state names.

This is a presentation-only mode over the existing dry-run planner. It does not execute actions, run validation commands, mutate files, deploy to Kubernetes, mutate ChatGPT Project Sources, delete ChatGPT Projects, or adopt artifacts.

## Changes

- Add `pb loop run --state-only --target <file>`.
- Add JSON output for `pb loop run --state-only --json` with `mode=state_only` and a `states` array.
- Keep the existing `pb loop run` default verbose dry-run output unchanged.
- Add focused CLI and loop tests proving state-only output is only state names and no execution semantics changed.
- Document MVP-0 foundation completion and MVP-1 state-only loop walkthrough opening.

## Example

```bash
pb loop run --target examples/loop-targets/static-game-dry-run-target.json --state-only
```

Expected text output:

```text
INTAKE
REQUIREMENTS_CHECK
PLAN
ACT_STUB
TEST_STUB
VERIFY_STUB
DIAGNOSE_STUB
CORRECT_STUB
DEPLOY_GATE_STUB
SOLVED
```

JSON variant:

```bash
pb loop run --target examples/loop-targets/static-game-dry-run-target.json --state-only --json
```

returns a side-effect-free payload with:

```text
action=loop_run
mode=state_only
dry_run=true
side_effects_performed=false
safety.commands_executed=false
safety.kubernetes_mutation_performed=false
safety.project_source_mutation_performed=false
safety.artifact_adoption_performed=false
```

## Safety boundaries

```text
no command execution
no test command execution
no file mutation
no Docker build/push
no Kubernetes apply
no Helm release
no deployment
no Project Source mutation
no artifact adoption/current behavior change
no ChatGPT Project deletion
```

## Focused validation

```bash
python3 -m pytest -q tests/test_promptbranch_loop.py tests/test_cli_loop.py tests/test_promptbranch_version.py tests/test_project_control_surface.py
python3 -m compileall -q promptbranch_loop.py promptbranch_cli.py promptbranch_version.py
python3 promptbranch_cli.py loop run --target examples/loop-targets/static-game-dry-run-target.json --state-only
python3 promptbranch_cli.py loop run --target examples/loop-targets/static-game-dry-run-target.json --state-only --json
python3 promptbranch_cli.py artifact guard --zip /mnt/data/chatgpt_claudecode_workflow-2_v0.1.92.zip --version v0.1.92 --json
python3 promptbranch_cli.py artifact verify /mnt/data/chatgpt_claudecode_workflow-2_v0.1.92.zip --json
```

Full release-control/adoption remains required before calling this accepted/current.
