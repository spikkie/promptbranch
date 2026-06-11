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


## Registry resolution rule

When a repository has `.promptbranch-repo.json`, Promptbranch uses the project-scoped registry by default:

```text
~/.local/state/promptbranch/projects/<project_id>/promptbranch_artifacts.json
```

An explicit `--profile-dir` remains the override/debug escape hatch. A default-resolved repo-local `.pb_profile` must not disable project registry resolution.

## Migration note

`pb project join` creates the project registry file if it does not exist, but it does not automatically adopt artifacts or migrate old repo-local `.pb_profile/promptbranch_artifacts.json` records. Use adoption/register workflows deliberately so Project Source verification remains explicit.


## Import existing repo-local current registry

`pb project join` creates the identity file and project registry, but it does not copy old repo-local current state automatically. To migrate existing local current records, run an explicit dry-run first from a joined repo:

```bash
pb project import-current-registry --dry-run --json
```

By default the command reads from the current repo's legacy profile:

```text
<repo>/.pb_profile/promptbranch_artifacts.json
```

and plans imports into:

```text
~/.local/state/promptbranch/projects/<project_id>/promptbranch_artifacts.json
```

Use an explicit source profile when importing from another checked-out repo or preserved legacy profile:

```bash
pb project import-current-registry --from-profile-dir /path/to/repo/.pb_profile --dry-run --json
```

If the dry-run is correct, run without `--dry-run`:

```bash
pb project import-current-registry --json
```

Conflicting current records fail closed. Use `--replace` only when the dry-run shows that replacing the existing project-registry current record is intentional:

```bash
pb project import-current-registry --replace --json
```

After import, verify from every joined repo:

```bash
pb repo list --json
pb repo doctor --json
pb artifact current --all --json
```

## Canonical artifact names for multi-repo adoption

From v0.1.73 onward, project-scoped artifact adoption expects canonical artifact filenames:

```text
<repo_id>_<version>.zip
```

The version token is always `v`-prefixed in the filename, even if the repo's internal `VERSION` file is bare.

Examples:

```text
architecture-process_v0.29.0.zip
ib_forex_trading_v0.248.3.1.zip
candlecast-src_v0.19.5.94.1.zip
```

When seeding a project registry from local historical ZIPs, copy legacy names to canonical names first, then adopt with explicit repo scope:

```bash
pb artifact adopt architecture-process_v0.29.0.zip --repo architecture-process --local-path ~/git/architecture-process/architecture-process_v0.29.0.zip --local-only --json
pb artifact adopt ib_forex_trading_v0.248.3.1.zip --repo ib_forex_trading --local-path ~/git/ib_forex_trading/source/ib_forex_trading_v0.248.3.1.zip --local-only --json
pb artifact adopt candlecast-src_v0.19.5.94.1.zip --repo candlecast-src --local-path ~/git/candlecast-src/candlecast-src_v0.19.5.94.1.zip --local-only --json
```

`--from-project-source` remains available when the ZIP is already present exactly once in ChatGPT Project Sources.
