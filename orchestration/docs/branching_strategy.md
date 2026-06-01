# Branching Strategy — JSON Orchestration State MVP v0.1.0

## Stable baseline

`main` remains the fixed Final Artifact Intake MVP baseline:

```text
main
  accepted artifact/source baseline: chatgpt_claudecode_workflow_v0.0.278.86.zip
  status: fixed Final Artifact Intake MVP
```

Recommended tags:

```text
final-artifact-intake-mvp-v0.0.278.86
chatgpt_claudecode_workflow_v0.0.278.86
```

## New MVP branch

The JSON Orchestration State MVP starts on:

```text
mvp/json-orchestration-state-v0.1.0
```

This branch starts from `main` at v0.0.278.86.

## Versioning rule

`v0.1.0` is a normal new minor-version MVP foundation release, not a repair release for `v0.0.278.86`.

```text
v0.0.278.86 = repair/final accepted baseline for Artifact Intake MVP
v0.1.0     = new JSON Orchestration State MVP foundation line
```

## Merge rule

Merge the branch back to `main` only after:

```text
- v0.1.0 ZIP is built from v0.0.278.86
- focused tests pass
- ZIP hygiene passes
- artifact intake/finalizer accepts v0.1.0
- pb artifact current reports v0.1.0
- pb artifact candidate-next has no unsafe stale action
- working tree is clean
```

Recommended merge style:

```bash
git switch main
git pull --ff-only
git merge --no-ff mvp/json-orchestration-state-v0.1.0
git push
```

## Authority distinction

```text
Git branch = source development line
Promptbranch artifact current = accepted release/source baseline
```

Promptbranch remains release authority.
