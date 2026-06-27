# Release v0.1.94 — MVP-1 read-only loop execution preflight

## Scope

`v0.1.94` is a normal MVP-1 development slice built from accepted/current `chatgpt_claudecode_workflow-2_v0.1.93.1.zip`.

The slice adds the first controlled read-only execution step for the loop runner:

```bash
pb loop run --target examples/loop-targets/static-game-dry-run-target.json --read-only-checks
```

The command performs bounded local read-only inspection of the target-declared path scopes and validation command declarations. It executes no shell commands, runs no tests, mutates no files, performs no Kubernetes/Docker/Helm deployment, mutates no Project Sources, adopts no artifacts, and never deletes ChatGPT Projects.

## Behavior

Text mode reports the inspected state, allowed path scope checks, validation command declarations, and explicit side-effect counters:

```text
status=read_only_checks_passed
mode=read_only_execution
target_id=k8s-game-static-dry-run
executed_state=REQUIREMENTS_CHECK
execution_mode=local_read_only_preflight
allowed_path=examples/k8s-game/** safe=true glob=true match_count=0 mutation_performed=false
validation_command=pytest -q tests/test_k8s_game_static.py execution_status=not_executed_read_only
commands_executed=0
side_effects_performed=false
```

JSON mode emits schema `promptbranch.loop.read_only_execution` with `mode=read_only_execution`, `execution_mode=local_read_only_preflight`, `executed_state=REQUIREMENTS_CHECK`, `checks.allowed_paths`, `checks.validation_commands`, and the standard no-mutation safety flags.

## Safety boundaries

- Path checks reject absolute paths, `..` traversal, and `~` home prefixes.
- Glob matching is read-only and bounded to a sample.
- Validation commands are inspected as declarations only; they are not executed.
- `--read-only-checks`, `--state-only`, and `--planned-actions` are mutually exclusive.
- Existing `pb loop validate`, `pb loop plan`, `pb loop run`, `--state-only`, and `--planned-actions` semantics are preserved.

## Validation

Focused validation performed for this candidate:

```bash
python3 -m pytest -q tests/test_promptbranch_loop.py tests/test_cli_loop.py tests/test_promptbranch_version.py tests/test_project_control_surface.py
python3 -m compileall -q .
bash -n chatgpt_claudecode_workflow_release_control.sh
python3 promptbranch_cli.py loop run --target examples/loop-targets/static-game-dry-run-target.json --read-only-checks
python3 promptbranch_cli.py loop run --target examples/loop-targets/static-game-dry-run-target.json --read-only-checks --json
```

Full live release-control/adoption is still required before accepted/current status.
