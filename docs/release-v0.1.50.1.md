# Release v0.1.50.1

Repair release for `v0.1.50`.

## Base release

`chatgpt_claudecode_workflow-2_v0.1.50.zip`

## Repair reason

The `v0.1.50` release lifecycle scheduler integration correctly planned release/source locks, but lifecycle planning could still surface a stale accepted artifact registry baseline such as `v0.1.40 -> v0.1.41` as a warning rather than an explicit reconciliation gate. Before routing future lifecycle execution, operators need a deterministic read-only reconciliation surface that explains how to advance local artifact/source current state to the installed/current release artifact.

## Files changed

- `VERSION`
- `pyproject.toml`
- `promptbranch_version.py`
- `promptbranch_cli.py`
- `docs/release-v0.1.50.1.md`
- `tests/test_cli_parser.py`
- `tests/test_promptbranch_cli.py`

## Behavior

Adds:

```bash
pb release reconcile-current \
  --artifact ./chatgpt_claudecode_workflow-2_v0.1.50.zip \
  --version v0.1.50 \
  --target-version v0.1.51 \
  --json
```

The command is read-only. It verifies the intended current artifact, compares it with `pb artifact current` roles, and emits the exact guarded adoption command needed to reconcile local artifact/source state:

```bash
pb artifact adopt chatgpt_claudecode_workflow-2_v0.1.50.zip \
  --from-project-source \
  --local-path ./chatgpt_claudecode_workflow-2_v0.1.50.zip \
  --json
```

`pb release lifecycle --plan --json` now embeds `current_reconciliation` and blocks lifecycle execution planning when the current artifact/source/registry baseline is stale relative to the requested artifact.

## Validation performed

- `python3 -m compileall -q .`
- focused parser and reconciliation tests
- release lifecycle dry-run JSON smoke
- artifact roundtrip ZIP verification
- ZIP root/hygiene inspection

## Scope control

No slice or line was advanced. This repair does not add live lifecycle phase routing, source mutation execution, artifact adoption execution, policy sync execution, or Git mutation. It only adds a read-only reconciliation planner and a lifecycle execution gate for stale current baseline state.
