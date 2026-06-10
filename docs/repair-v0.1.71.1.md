# Repair v0.1.71.1 — Project registry command alignment

## Base release

```text
chatgpt_claudecode_workflow-2_v0.1.71.zip
```

## Repair version

```text
chatgpt_claudecode_workflow-2_v0.1.71.1.zip
```

## Reason

v0.1.71 field testing showed that `pb project join` created `.promptbranch-repo.json` and local repo configuration, and `pb repo list` / `pb repo doctor` read the new project-scoped registry. However, `pb artifact current --all` could still read the repo-local `.pb_profile` registry because the CLI resolved a default profile directory before command handling, and the project registry resolver treated that resolved default as if the operator had explicitly passed `--profile-dir`.

This created split truth between:

```text
~/.local/state/promptbranch/projects/<project_id>/promptbranch_artifacts.json
<repo>/.pb_profile/promptbranch_artifacts.json
```

## Files changed

```text
promptbranch_project.py
promptbranch_cli.py
tests/test_promptbranch_project.py
tests/test_promptbranch_repos.py
docs/project/definition-of-done.md
docs/project/plan.md
docs/project/status.md
docs/project/release-status.md
docs/project/decisions.md
docs/promptbranch-multi-repo-projects.md
docs/repair-v0.1.71.1.md
VERSION
pyproject.toml
promptbranch_version.py
```

## Repair behavior

```text
- `pb project join` ensures the project registry file exists.
- Project registry resolution is disabled only when `--profile-dir` is explicitly supplied.
- A default-resolved profile directory no longer disables project registry resolution.
- `pb artifact current --all` includes configured repo IDs from the project repo registry when reading project-scoped state.
- `pb repo list`, `pb repo doctor`, and `pb artifact current --all` use the same project registry by default from joined repos.
- Explicit `--profile-dir` remains the debug/override path.
- Missing repo lookup still fails closed.
```

## Validation performed

```text
Focused project/repo/artifact-current tests.
Project control-surface tests.
Python compileall.
ZIP hygiene and clean extraction focused validation.
```

Full test suite was not run during candidate creation.

## Scope confirmation

```text
No normal slice advanced.
No release-set orchestration added.
No dependency solving added.
No Project Source upload automation added.
No automatic artifact adoption added.
No deployment behavior changed.
```
