# Release v0.1.87 — Loop target schema and dry-run planner

## Baseline

```text
chatgpt_claudecode_workflow-2_v0.1.86.zip
```

## Slice

`v0.1.87` opens the first executable Promptbranch loop-planning slice after the accepted/current `v0.1.86` baseline.

The release adds a deterministic target-definition schema and a dry-run planner for the loop-based problem-solving MVP. The planner is intentionally side-effect free: it validates target requirements, emits planned loop states, and reports safety flags, but it does not execute commands, mutate files, deploy to Kubernetes, mutate Project Sources, or adopt artifacts.

## Changes

- Add `promptbranch_loop.py` with target schema validation and dry-run planning.
- Add `pb loop validate --target <file> [--json]`.
- Add `pb loop plan --target <file> [--json]`.
- Add `pb loop run --target <file> [--dry-run] [--json]` as stubbed control-flow output only.
- Add `examples/loop-targets/static-game-dry-run-target.json` as the first future k8s-game target fixture.
- Add `examples/loop-targets/missing-requirements-target.json` for requirements-missing classification.
- Update the project control surface from k8s-game-first planning to loop-first MVP planning.

## Safety boundaries

```text
no real implementation actions
no validation command execution
no file mutation by the loop
no Docker build/push
no Kubernetes apply
no Helm release
no deployment
no Project Source mutation
no artifact adoption/current behavior change
no ChatGPT Project deletion
```

Every planned event carries `side_effects_performed=false` and explicit false safety flags for mutation, deployment, Project Source mutation, artifact adoption, and project deletion.

## Focused validation

```bash
python3 -m pytest -q tests/test_promptbranch_loop.py tests/test_cli_loop.py tests/test_promptbranch_version.py tests/test_project_control_surface.py
python3 -m compileall -q promptbranch_loop.py promptbranch_cli.py promptbranch_state.py promptbranch_version.py
python3 promptbranch_cli.py loop validate --target examples/loop-targets/static-game-dry-run-target.json --json
python3 promptbranch_cli.py loop plan --target examples/loop-targets/static-game-dry-run-target.json --json
python3 promptbranch_cli.py loop run --target examples/loop-targets/static-game-dry-run-target.json --json
python3 promptbranch_cli.py artifact guard --zip ~/Downloads/chatgpt_claudecode_workflow-2_v0.1.87.zip --version v0.1.87 --json
python3 promptbranch_cli.py artifact verify ~/Downloads/chatgpt_claudecode_workflow-2_v0.1.87.zip --json
```

Full release-control/adoption remains required before calling this accepted/current.
