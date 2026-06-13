# Release v0.1.75

## Type

```text
normal candidate
```

## Baseline

```text
chatgpt_claudecode_workflow-2_v0.1.74.3.zip
```

## Slice

```text
KISS project/repo management command model
```

## Summary

This release rebases the KISS project/repo management solution onto the operator-pinned v0.1.74.3 baseline.

The goal is one command/state model for all projects:

```text
1 repo or 10 repos -> same project repo loop -> same JSON shape -> same operator commands
```

## Behavior

- `pb artifact current --json` in a joined project returns the project repo-loop payload shape.
- `pb artifact current --all --json` remains compatible and returns the same loop shape.
- `pb artifact current --repo <repo> --json` filters the same repo-loop model.
- `pb project status --json` includes the same repo inventory payload as `pb repo list --json`.

## Out of scope

- Release-set orchestration.
- Dependency solving.
- Automatic cross-repo adoption.
- Project Source upload behavior.
- Browser automation behavior.
- Docker/deployment behavior.

## Validation

Focused validation required before acceptance:

```bash
python3 -m pytest -q tests/test_promptbranch_project.py tests/test_promptbranch_repos.py tests/test_project_control_surface.py tests/test_promptbranch_version.py
python3 -m pytest -q tests/test_promptbranch_artifacts.py tests/test_promptbranch_cli.py -k "adopt or artifact_current or local_only or local_artifact_not_found or promptbranch_repo or baseline_status or mvp_status"
python3 -m compileall -q .
```

Full release-control and adoption evidence remain required before accepted/current status.
