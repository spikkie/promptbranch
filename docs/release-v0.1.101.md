# Release v0.1.101

## Slice

Read-only command result diagnosis and blocked/failed classification.

## Baseline

Accepted/current baseline: `chatgpt_claudecode_workflow-2_v0.1.100.3.zip`.

## Scope

- Add `promptbranch.loop.read_only_command_diagnosis` as an evidence-only schema.
- Add `pb loop run --diagnose-read-only-result` behind `--read-only-execution --evidence-gate --execute-read-only-validation`.
- Classify read-only command evidence as `passed`, `blocked`, or `failed`.
- Preserve blocked and failed reason codes for operator review.
- Keep correction-plan generation and file mutation out of scope.

## Safety boundaries

The diagnosis path does not execute extra commands, retry commands, generate correction plans, write files, deploy, mutate Project Sources, adopt artifacts, or delete ChatGPT Projects.

## Validation

Focused validation covers loop diagnosis, CLI diagnosis, control-surface state, version surface, compileall, shell syntax, Artifact Guardian, and artifact verification. Full release-control/adoption must still be run externally before accepting the artifact.
