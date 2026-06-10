# Repair v0.1.71.3 — ZIP protected-entry hygiene

## Base release

```text
chatgpt_claudecode_workflow-2_v0.1.71.2.zip
```

## Repair version

```text
v0.1.71.3
```

## Reason

The v0.1.71.2 candidate failed the release ZIP import guard because it packaged protected local Promptbranch state:

```text
.pb_profile/.promptbranch_state.json
```

## Files changed

```text
VERSION
pyproject.toml
promptbranch_version.py
docs/repair-v0.1.71.3.md
```

The protected `.pb_profile/` directory was removed from the ZIP payload.

## Scope confirmation

This is a packaging hygiene repair only. It does not advance the v0.1.71 normal slice, does not add release-set orchestration, and does not change runtime behavior beyond the version surfaces needed for the repair artifact.

## Validation

```text
required root files present
protected ZIP entries absent
ZIP root layout is repo_root
focused project/repo tests run
compileall run
```
