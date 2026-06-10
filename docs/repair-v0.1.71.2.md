# Repair v0.1.71.2 — Required root file packaging repair

## Base release

```text
chatgpt_claudecode_workflow-2_v0.1.71.1.zip
```

## Repair version

```text
chatgpt_claudecode_workflow-2_v0.1.71.2.zip
```

## Reason

The v0.1.71.1 repair candidate failed the install ZIP import guard during `== Verify install ZIP ==` because the ZIP was missing a required repository-root file:

```text
.gitignore
```

This is a packaging-layout defect, not a functional scope change.

## Files changed

```text
.gitignore
VERSION
pyproject.toml
promptbranch_version.py
docs/project/definition-of-done.md
docs/project/plan.md
docs/project/status.md
docs/project/release-status.md
docs/project/decisions.md
docs/repair-v0.1.71.2.md
```

## Repair behavior

```text
- Restore required root `.gitignore` into the release ZIP.
- Preserve all v0.1.71.1 project-registry command-alignment changes.
- Keep ZIP root as repository contents with no wrapper folder.
- Do not advance the normal release line.
```

## Validation performed

```text
Focused project/repo/artifact-current tests.
Project control-surface tests.
Python compileall.
Required root-file check.
ZIP hygiene and clean extraction focused validation.
```

Full test suite was not run during candidate creation.

## Scope confirmation

```text
No normal slice advanced.
No implementation behavior changed beyond preserving v0.1.71.1 code.
No release-set orchestration added.
No dependency solving added.
No Project Source upload automation added.
No automatic artifact adoption added.
No deployment behavior changed.
```
