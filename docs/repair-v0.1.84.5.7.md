# Repair v0.1.84.5.7 — shared live Project ensure command repair

## Base

- Accepted/current baseline remains `chatgpt_claudecode_workflow-2_v0.1.84.5.zip` until a later adoption/current proof exists.
- Repair base: `v0.1.84.5.6` repair candidate.

## Reason

`v0.1.84.5.6` introduced the correct `--run-all-tests` live-phase intent: create or ensure one shared run-scoped ChatGPT Project and reuse its exact Project URL for `ask-live`, `visual-artifact-roundtrip`, and `release-live`.

The implementation called a non-existent nested CLI surface:

```bash
pb project ensure ...
```

The supported operator CLI is the top-level command:

```bash
pb project-ensure ...
```

## Changes

- Release-control `live_project_ensure` now calls `pb --profile-dir <seed-dir> project-ensure <name> --memory-mode project-only --keep-open`.
- The returned JSON is still parsed for `project_url` and exported as `shared_live_project_url`.
- The shared URL is still passed to `ask-live`, `visual-artifact-roundtrip`, and `release-live` using `--conversation-url`.
- Focused shell regressions now assert the supported top-level `project-ensure` command.

## Scope boundaries

No change to:

- Project deletion policy; deletion remains frozen.
- Ledger creation, ledger append, or `accept-event --write`.
- Project Source mutation behavior.
- Artifact adoption/current semantics.
- Deployment behavior.
- Model execution authority.

## Validation performed

- Focused release-control shell tests for shared live Project reuse.
- Recovered-rate-limit retry suppression regression tests.
- Version/control-surface tests.
- `python3 -m compileall -q .`.
- `bash -n chatgpt_claudecode_workflow_release_control.sh`.
- `python3 promptbranch_cli.py orchestration validate-ledger --json`.
- Artifact Guardian.
- ZIP hygiene.

## Acceptance status

Repair candidate only. Not accepted/current without later full all-tests/adoption/current evidence.
