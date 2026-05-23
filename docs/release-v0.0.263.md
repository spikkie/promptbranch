# Release v0.0.263

## Scope

Normal development release from accepted baseline `chatgpt_claudecode_workflow_v0.0.262.zip`.

This release takes a larger but still controlled step toward the Promptbranch-as-Claude-Code-shell operating model by expanding the read-only native agent/skill layer. It intentionally avoids source mutation, artifact adoption, Git mutation, browser automation changes, or write-capable MCP execution.

## Changes

- Added built-in read-only `release-readiness` skill.
- `pb skill list/show/validate` now exposes and validates `release-readiness`.
- `pb agent run --skill release-readiness "check release readiness" --json` plans these read-only MCP calls:
  - `filesystem.read VERSION`
  - `artifact.registry.current`
  - `git.status`
  - `git.diff.summary`
- `pb agent run` now emits a structured `report` for supported skills:
  - `repo-inspection` reports version, Git branch/SHA, dirty state, diff summary, and mutation status.
  - `release-readiness` reports VERSION, adopted/current artifact metadata, Git cleanliness, version/baseline comparison signals, and release readiness status.
- Safety model remains read-only:
  - no source sync
  - no artifact release/adopt
  - no Git commit/push
  - no browser mutation
  - no model execution authority

## Validation

Performed by the release builder:

- `python3 -m compileall -q .`
- focused MCP/skill tests
- focused parser/runtime version tests
- extracted ZIP smoke checks
- ZIP hygiene verification

## Operator notes

Useful new command:

```bash
pb agent run --skill release-readiness "check release readiness" --path . --json | python3 -m json.tool
```

The command is intended as a safe preflight/readiness view before release work. It does not replace the strict finalizer or Artifact Intake MVP gate.
