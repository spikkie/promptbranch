# Repair v0.1.70.1

## Base release

```text
chatgpt_claudecode_workflow-2_v0.1.70.zip
```

## Repair version

```text
chatgpt_claudecode_workflow-2_v0.1.70.1.zip
```

## Reason

Field testing of the v0.1.70 multi-repo artifact registry showed that valid repo lookups, `--all`, and ambiguous unscoped-current behavior worked, but an explicit missing repo lookup could fall back to legacy/global artifact state and display another repo artifact under the requested repo id.

## Scope

In scope:

```text
- prevent explicit missing repo lookup fallback in ConversationStateStore.snapshot
- return repo_current_not_found for pb artifact current --repo <missing> when no repo-scoped state or registry entry exists
- keep non-JSON missing-repo output safe
- add focused regression tests
- update version and project control-surface status
```

Out of scope:

```text
- no slice advancement
- no line advancement
- no release-set orchestration
- no .promptbranch-repos.json project declaration
- no pb repo list/doctor commands
- no lifecycle/adoption behavior changes
- no deployment behavior changes
```

## Files changed

```text
promptbranch_state.py
promptbranch_cli.py
tests/test_cli_state.py
tests/test_promptbranch_cli.py
VERSION
pyproject.toml
promptbranch_version.py
docs/project/definition-of-done.md
docs/project/plan.md
docs/project/status.md
docs/project/release-status.md
docs/project/decisions.md
docs/repair-v0.1.70.1.md
```

## Validation performed

```text
python3 -m pytest -q tests/test_cli_state.py -k 'repo_artifact or legacy_artifact or missing_repo'
python3 -m pytest -q tests/test_promptbranch_cli.py -k 'artifact_current_missing_repo or artifact_current_all_returns_all_repo_payloads or artifact_current_without_repo_blocks_when_multiple_repos_exist or artifact_current_repo_arg_returns_repo_scoped_payload'
python3 -m pytest -q tests/test_promptbranch_artifacts.py tests/test_cli_state.py tests/test_promptbranch_cli.py -k 'artifact_current or artifact_adopt or repo_artifact or missing_repo'
python3 -m pytest -q tests/test_project_control_surface.py
python3 -m compileall -q .
```

## Explicit non-advancement statement

```text
This repair does not advance the v0.1.x release line, does not open a new normal slice, and does not add new multi-repo project-declaration capability. It fixes only a defect in the intended v0.1.70 repo-scoped artifact current behavior.
```
