# Release v0.1.71 — Project-scoped multi-repo registry resolution

## Type

```text
normal candidate
```

## Baseline

```text
chatgpt_claudecode_workflow-2_v0.1.70.1.zip
```

## Goal

Make multi-repo Promptbranch projects foolproof for multiple developers: any joined repo can resolve the same project artifact registry automatically without remembering a coordinator/main repo or manual `--profile-dir`.

## In scope

- `.promptbranch-repo.json` repo identity support.
- Project registry path under user-local state: `~/.local/state/promptbranch/projects/<project_id>/promptbranch_artifacts.json`.
- User-local joined repo registry: `~/.config/promptbranch/projects/<project_id>/repos.json`.
- `pb project join --json`.
- `pb project status --json`.
- `pb repo list --json`.
- `pb repo doctor --json`.
- `pb artifact current --all --json` project diagnostics for joined repos.
- Regression coverage that missing repo lookup still fails closed.

## Out of scope

- Release-set orchestration.
- Cross-repo dependency solving.
- Automatic Project Source upload.
- Automatic artifact adoption.
- Git operations across repositories.
- Deployment orchestration.
- Treating any repo as a hardcoded main repo.

## Validation

```text
focused project/repo tests: passed
artifact-current regression tests: passed
project control-surface tests: passed
compileall: passed
ZIP hygiene: passed
full test suite: not run
```
