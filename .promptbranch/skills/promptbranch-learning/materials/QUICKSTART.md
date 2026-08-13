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

## 6. Install or update PB skills in an external repository

Use `skill sync` from a Promptbranch control-plane repository to teach an external Git repository the exact **accepted/current** PB skill contract. The source worktree is used only to resolve tracked Project/repository identity; skill content is exported from the immutable adopted/current artifact.

```sh
pb skill sync \
  --path "$HOME/git/chatgpt_claudecode_workflow-2" \
  --target "$HOME/git/my_vault" \
  promptbranch-learning \
  promptbranch-operator \
  promptbranch-tool-authoring \
  --json
```

Omit the skill names to sync all three portable PB skills. Use `--dry-run` to resolve authority, build and verify bundles, and report the plan without changing the target. A repeated sync is idempotent. Managed local edits fail closed; `--force` is required to replace such drift.

The command writes `.promptbranch/promptbranch-skills.json` in the target with the source PB version, authoritative artifact SHA-256, per-bundle SHA-256, and installed tree digests. It validates each installed `SKILL.md` and reports Git status, but does not commit or push the target repository.
