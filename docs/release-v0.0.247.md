# Release v0.0.247

## Scope

Normal release from `chatgpt_claudecode_workflow_v0.0.246.zip`.

This slice adds the first read-only native release lifecycle configuration surface:

```bash
pb release config --json
```

## Invariants

The command is diagnostic only. It must not:

- install ZIPs
- download artifacts
- upload Project Sources
- migrate candidates
- adopt artifacts
- update Promptbranch state
- commit or push Git state

## Implemented

- Added `.promptbranch-release.yml` to the repo root.
- Added a dependency-free YAML-subset parser for release lifecycle config.
- Added validation for:
  - `schema_version`
  - `artifact.prefix`
  - `artifact.suffix`
  - `artifact.version_file`
  - `artifact.policy_file`
  - `install.preserve`
  - `git.unsafe_paths`
  - hook command placeholders: `{version}`, `{target_version}`, `{artifact}`, `{repo_path}`
- Added `pb release config --config PATH --repo-path PATH --json`.

## Boundary

This is not `pb release lifecycle` yet. It only validates the local lifecycle configuration that future install/test/adopt commands will use.
