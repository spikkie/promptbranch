# Repair v0.1.94.1 — Project Source capacity-prune identity guard

## Type

Repair-only candidate for the intended `v0.1.94` release.

## Base

```text
latest accepted/current baseline before v0.1.94: chatgpt_claudecode_workflow-2_v0.1.93.1.zip
failed candidate line:                  chatgpt_claudecode_workflow-2_v0.1.94.zip
repair version:                         v0.1.94.1
```

## Reason

The `v0.1.94 --run-all-tests --adopt-after-validation` run failed during Project Source add for the candidate ZIP. Capacity pruning selected the old same-family release source `chatgpt_claudecode_workflow-2_v0.1.85.zip`, but the remove operation drifted to different Project Source rows before the target disappeared.

Observed failure signature:

```text
status: source_limit_prune_remove_failed
capacity_prune_source_name: chatgpt_claudecode_workflow-2_v0.1.85.zip
capacity_prune_remove_error: Project source remove drifted to a different row before the target disappeared
operator_review_required: true
```

The defect was not in the `v0.1.94` read-only loop execution behavior. It was a release/adoption safety defect in Project Source capacity-prune retry handling: after an exact remove reported identity drift, the add path still attempted a looser retry. That is unsafe because it can remove collateral rows.

## Scope

This repair preserves the intended `v0.1.94` first controlled read-only execution step and adds a Project Source capacity-prune identity guard.

In scope:

- Add `pb loop run --read-only-execution` for local read-only target preflight.
- Inspect target-declared `allowed_paths` as repo-relative/read-only path scopes.
- Inspect target-declared validation commands without executing them.
- Keep all loop execution side effects blocked.
- Stop capacity-prune removal immediately when exact remove reports identity drift or collateral removal.
- Suppress the looser capacity-prune retry after identity drift.
- Add regression tests for read-only loop preflight and no-retry capacity-prune drift handling.

Out of scope:

- No command execution from loop targets.
- No file mutation from loop targets.
- No Kubernetes apply, Docker push, Helm release, deployment, or post-deploy verification.
- No Project Source mutation from the loop engine.
- No artifact adoption/current behavior change.
- No ChatGPT Project deletion behavior change.
- No broad Project Source pruning rewrite beyond the drift/no-retry guard.

## Files changed

```text
VERSION
pyproject.toml
promptbranch_version.py
promptbranch_loop.py
promptbranch_cli.py
promptbranch_browser_auth/client.py
tests/test_promptbranch_loop.py
tests/test_cli_loop.py
tests/test_project_source_capabilities.py
tests/test_promptbranch_version.py
docs/repair-v0.1.94.1.md
docs/release-v0.1.94.1.md
docs/project/definition-of-done.md
docs/project/decisions.md
docs/project/migration.md
docs/project/plan.md
docs/project/release-status.md
docs/project/status.md
```

## Validation performed

Focused validation performed for this candidate:

```text
pytest targeted read-only loop and capacity-prune drift tests
pytest loop/CLI/version/project-control focused tests
compileall for changed Python surfaces
release-control shell syntax
Artifact Guardian
artifact verify / ZIP hygiene
```

Full release-control, live browser validation, Project Source add/verify, adoption/current verification, and `pb artifact current --json` remain required before this repair can be called accepted/current.

## Slice advancement

No normal slice advances in this repair. `v0.1.94.1` repairs the intended `v0.1.94` release/adoption safety defect only while preserving the intended read-only execution slice.
