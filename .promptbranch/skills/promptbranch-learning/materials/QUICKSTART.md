# Promptbranch learning quickstart

The quickstart is deliberately read-first.

## 1. Confirm the CLI and skill surfaces

```sh
pb --help
pb skill list --json
pb skill validate promptbranch-learning --path . --json
pb skill validate promptbranch-operator --path . --json
```

## 2. Inspect current PB identities

When a workspace/profile is configured, inspect rather than mutate:

```sh
pb ws current --json
pb task current --json
pb artifact current --json
```

If the repository itself is the learning target, also read `VERSION`, `.promptbranch-repo.json`, `.promptbranch-ai.json`, and `docs/project/plan-state.json`.

## 3. Inspect operator state

Use `git status` and `git diff`/PB read-only equivalents before proposing repository changes. Resolve the current artifact and project identity before release-related work.

## 4. Validate learning material

```sh
pb skill learning-validate --path . --json
pb skill operator-validate --path . --json
```

## 5. Export portable learning material

```sh
pb skill export promptbranch-learning --path . --output /tmp/promptbranch-learning.zip --json
pb skill verify-bundle /tmp/promptbranch-learning.zip --json
```

A successful export/verification proves bundle integrity and content contract. It does not grant execution authority.
