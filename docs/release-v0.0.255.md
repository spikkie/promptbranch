# Release v0.0.255 — guarded Git sync execution and final lifecycle summary

## Scope

`v0.0.255` continues from accepted `v0.0.254` and closes the next native lifecycle gap:

- add guarded `pb release git-sync`
- support read-only Git sync planning
- support explicit `--commit`
- support explicit `--push` only after a same-run guarded commit
- integrate Git sync into `pb release lifecycle`
- improve final lifecycle summary with Git sync eligibility and performed-state fields

## Safety boundary

Default behavior remains non-committing and non-pushing.

Git commit requires:

- explicit `--commit`
- valid release config
- verified artifact ZIP
- policy file synchronized to the accepted artifact/source baseline
- no unsafe dirty paths
- no unexpected dirty paths when configured expected paths are present

Git push requires:

- explicit `--push`
- explicit `--commit`
- successful same-run guarded commit
- configured upstream branch
- local branch not behind upstream

Unsafe paths remain blocked by release config, including ZIP files, logs, `.env`, `.pb_profile/`, generated state, and cache paths.

## Commands

```bash
pb release git-sync --artifact ZIP --version VERSION --plan --json
pb release git-sync --artifact ZIP --version VERSION --commit --json
pb release git-sync --artifact ZIP --version VERSION --commit --push --json
```

`pb release lifecycle` now includes the Git sync phase. Without `--commit`, that phase is inspection/planning only.

## Non-goals

This release does not implement the real ChatGPT answer artifact download/migrate loop. That remains a separate proof step after local lifecycle closure.
