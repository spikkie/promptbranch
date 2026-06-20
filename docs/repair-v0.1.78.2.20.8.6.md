# Repair v0.1.78.2.20.8.6 — Project-scoped state authority for joined repos

## Release

`v0.1.78.2.20.8.6`

## Base release

`v0.1.78.2.20.8.5`

## Reason

Operator logs from a joined `my_awx` repository showed that `pb task use 6a296126-1708-83ed-a945-543a22c7027a` wrote the selected task to the project-scoped Kubernetes profile, while plain `promptbranch state` read the stale repo-local `.pb_profile/.promptbranch_state.json` file. The project profile had `conversation_id=6a296126-1708-83ed-a945-543a22c7027a` and `artifact_version=v0.0.212.4`; the repo-local profile still reported `conversation_url=null` and stale artifact state `my_awx_v0.0.200.8.zip`.

That is a state-authority split: joined multi-repo task/workspace/artifact state writes and reads must use the same project-scoped state store unless the operator explicitly supplies `--profile-dir`.

## Scope

Repair-only state-resolution consistency on top of `v0.1.78.2.20.8.5`:

- Make `build_backend()` construct its `ConversationStateStore` through the same project-aware `_state_store_from_args(args)` helper already used by task/source/artifact state commands.
- Preserve the resolved `args.profile_dir` as the browser profile path, so browser authentication/profile behavior remains repo-local or operator-supplied.
- Preserve explicit `--profile-dir` override behavior.
- Add focused regression tests proving joined repos read project-scoped state by default and explicit `--profile-dir` keeps the profile-state override.
- Preserve the immutable no-delete invariant from `v0.1.78.2.20.8.4` and the evidence-label consistency from `v0.1.78.2.20.8.5`.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `promptbranch_cli.py`
- `tests/test_promptbranch_repos.py`
- `tests/test_promptbranch_version.py`
- `docs/repair-v0.1.78.2.20.8.6.md`
- `docs/project/definition-of-done.md`
- `docs/project/status.md`
- `docs/project/release-status.md`
- `docs/project/plan.md`
- `docs/project/decisions.md`
- `docs/project/migration.md`

## Validation

Focused validation performed:

```bash
python3 -m pytest -q \
  tests/test_promptbranch_repos.py \
  tests/test_promptbranch_version.py \
  tests/test_project_control_surface.py
```

Additional validation performed:

```bash
python3 -m compileall -q .
bash -n chatgpt_claudecode_workflow_release_control.sh
```

Full release-control and live browser validation were not run in this environment.

## Explicit non-advancement statement

This repair does not advance a normal slice or line. It changes only state-store authority selection, version metadata, tests, and repair documentation on top of `v0.1.78.2.20.8.5`. Project deletion remains immutable-frozen.
