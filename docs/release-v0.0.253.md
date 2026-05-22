# Release v0.0.253

## Scope

Accelerated native release lifecycle slice from accepted baseline `chatgpt_claudecode_workflow_v0.0.252.zip`.

This release combines:

- `.promptbranch-project.json` policy sync to the accepted artifact/source baseline
- policy readback verification after sync
- Git safety planning with expected vs unsafe dirty path classification
- `pb release lifecycle --plan --json`
- no Git commit or push by default

## Commands added

```bash
pb release policy-sync \
  --artifact ZIP \
  --version VERSION \
  --target-version NEXT \
  --repo-path . \
  --json

pb release policy-sync \
  --artifact ZIP \
  --version VERSION \
  --repo-path . \
  --plan \
  --json

pb release lifecycle \
  --artifact ZIP \
  --version VERSION \
  --target-version NEXT \
  --repo-path . \
  --plan \
  --json
```

## Safety boundary

`policy-sync` mutates only the repo-local policy file and verifies readback. It does not mutate Project Sources, artifact registry, Promptbranch source/artifact state, or Git.

`lifecycle --plan` is read-only in this release. It composes the native lifecycle phases but executes no install, source upload, hook, adoption, policy sync, commit, or push.

Git behavior is planning-only. The git safety planner detects dirty paths, expected paths, unexpected paths, and configured unsafe path patterns. It does not stage, commit, or push.

## Validation

- Python compile smoke
- focused release lifecycle tests
- CLI parser smoke for new commands
- extracted ZIP smoke for `pb release lifecycle --plan --json`
- ZIP hygiene and layout verification
