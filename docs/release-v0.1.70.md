# Release v0.1.70

## Slice

```text
Multi-repo artifact registry state
```

## Baseline

```text
chatgpt_claudecode_workflow-2_v0.1.69.zip accepted/current by operator-provided Promptbranch adoption evidence.
```

## Summary

v0.1.70 makes Promptbranch artifact current-state repo-scoped so one repository's ZIP cannot overwrite or obscure another repository's accepted baseline inside the same ChatGPT Project.

## In scope

- Add portable `repo_id` support to artifact registry records.
- Add repo-aware `ArtifactRegistry.current(repo_id=...)`, `current_all()`, and ambiguous-current detection.
- Add repo-scoped project artifact/source state under `artifacts_by_repo`.
- Add `pb artifact current --repo <repo> --json`.
- Add `pb artifact current --all --json`.
- Make unscoped `pb artifact current --json` fail closed when multiple repo scopes exist.
- Record repo scope during artifact adoption and reject explicit repo/artifact-prefix mismatches.
- Add focused tests proving repo adoption/current-state isolation.

## Out of scope

- Release-set orchestration.
- Cross-repo dependency solving.
- Multi-repo lifecycle execution.
- Project Source upload behavior changes.
- ZIP packaging behavior changes.
- Runtime/deployment behavior changes.

## Validation

```text
focused artifact/state/CLI tests: passed during candidate build
project control-surface test: passed during candidate build
compileall: passed during candidate build
ZIP hygiene: passed during candidate build
full tests: not run here
```

## Acceptance rule

This ZIP remains candidate until operator adoption evidence confirms repo-scoped runtime, state artifact, state source, registry current, and consistency alignment.
