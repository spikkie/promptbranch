# Promptbranch multi-repo projects

## Purpose

A multi-repo Promptbranch project must not require developers to remember a coordinator or main repository.

Each joined repository declares its project identity in `.promptbranch-repo.json`. Promptbranch then derives a shared project registry path from `project_id` and stores artifact current-state under user-local state.

## Files

```text
repo/.promptbranch-repo.json
~/.local/state/promptbranch/projects/<project_id>/promptbranch_artifacts.json
~/.local/state/promptbranch/projects/<project_id>/.promptbranch_state.json
~/.config/promptbranch/projects/<project_id>/repos.json
```

## Join example

```bash
pb project join   --project-id kubernetes   --project-home-url https://chatgpt.com/g/g-p-6835d9419f3c8191b86b93e6379879f6-kubernetes/project   --repo-id my_awx   --artifact-pattern 'my_awx_<version>.zip'   --role consumer   --json
```

## Diagnostics

```bash
pb project status --json
pb repo list --json
pb repo doctor --json
pb artifact current --all --json
```

`--profile-dir` remains available as an explicit debug/override path.
