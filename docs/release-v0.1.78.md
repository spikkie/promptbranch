# Release v0.1.78 — AG-001 Deterministic Artifact Guardian Guard

## Status

```text
candidate
```

## Baseline

```text
chatgpt_claudecode_workflow-2_v0.1.77.11.zip accepted/current
```

## Slice

```text
AG-001 — Deterministic Artifact Guardian Guard
```

## Goal

Add a deterministic policy-driven ZIP guard so structurally invalid release artifacts fail before lifecycle install or operator/assistant handoff.

## In scope

- `.artifact-guardian.yml` project-local artifact policy.
- `promptbranch_artifact_guardian.py` policy loader and ZIP validator.
- `pb artifact guard` command.
- Required-entry checks.
- Forbidden-entry checks.
- Wrapper-folder layout checks.
- Nested ZIP checks.
- `VERSION` equality checks.
- Artifact filename pattern checks.
- Executable-bit checks for configured entries.
- Strict JSON output with `release_ready`.
- Regression test proving a ZIP missing `.gitignore` fails.
- Project control-surface updates.

## Out of scope

- `pb artifact build` integration.
- `pb artifact heal`.
- `pb artifact agent`.
- Lifecycle integration.
- Assistant-side handoff enforcement.
- Source adoption.
- Marking artifacts accepted/current.
- Deployment validation.
- Runtime correctness validation.
- k8s-game documentation, schemas, examples, state machines, or Draw.io roadmap.

## Validation expected before adoption

```bash
python3 -m pytest -q tests/test_artifact_guardian.py
python3 -m pytest -q tests/test_project_control_surface.py tests/test_promptbranch_version.py
python3 -m compileall -q .
bash -n chatgpt_claudecode_workflow_release_control.sh
bash -n scripts/post-release-validation.sh
```

The candidate remains non-current until release-control and `pb artifact current --all --json` adoption evidence confirm alignment.
