# Release v0.0.257 — ask-release candidate-producing protocol flow

Base release: `chatgpt_claudecode_workflow_v0.0.256.zip`

## Scope

Adds a controlled `pb ask-release` command that creates a strict candidate-producing Promptbranch ask/reply protocol turn.

The command is intentionally limited to protocol request/response validation. It does not download, migrate, test, adopt, commit, or push artifacts by itself.

## New command

```bash
pb ask-release "Implement the next slice" \
  --target-version v0.0.257 \
  --json
```

Inspection-only mode:

```bash
pb ask-release "Implement the next slice" \
  --target-version v0.0.257 \
  --print-request-json \
  --json
```

## Invariants

`pb ask-release` requires the reply to contain exactly one expected ZIP artifact candidate:

- expected filename: `<repo>_<target-version>.zip`
- expected version: target version
- expected role: `candidate_release`
- reply status: `completed`
- result type: `release_candidate`
- no-artifact/no-change replies are rejected

The command fails closed if the assistant reply is missing, invalid, stale, ambiguous, or does not include exactly one expected downloadable ZIP candidate.

## Boundary

The next executor remains:

```bash
pb artifact candidate-run \
  --execute-until-blocked \
  --require-complete \
  --require-real-candidate \
  --json
```

Git commit/push remain disabled unless explicitly requested elsewhere.
