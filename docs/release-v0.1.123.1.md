# Release v0.1.123.1 — Integrate complete MVP proof lifecycle into `pb ask`

## Classification

Repair release from accepted/current `v0.1.123`. It does not count as a normal MVP proof cycle and does not advance product scope.

## Problem

`v0.1.123` passed strict release validation and adoption, but the operator had to run separate parse, intake, release-control, and finalizer commands. A later `--latest` lookup selected an older `no_artifact` continuation reply, so chronological candidate intake was not proven and cycle 1 could not count.

## Repair

The exact operator command

```bash
pb ask continue --target-version v0.1.124 --release-type normal
```

now owns one complete proof cycle. Internally it:

1. resolves accepted/current and the next normal target;
2. sends a strict release-candidate Ask;
3. captures exact request, conversation, message, and answer identity;
4. performs artifact intake with those exact selectors, never generic `--latest`;
5. requires real download, ZIP verification, migration, and matching SHA-256;
6. runs strict release control with Project Source publication, 10/10 validation, adoption, and current verification;
7. runs the fail-closed continuation preflight and continuation Ask;
8. writes the canonical proof artifact and reports `1/2` or `2/2` only after every stage passes.

Any failed stage returns nonzero and cannot print a verified or complete status. Full subprocess output is retained in version-scoped evidence files; the terminal result contains only bounded tails, exact evidence paths, and compact parsed verdict fields.

## Strict sequence after repair acceptance

```text
v0.1.124 → MVP proof cycle 1
v0.1.125 → MVP proof cycle 2 and final MVP verdict
```

## Validation commands

```bash
python3 -m pytest -q tests/test_promptbranch_mvp_ask_lifecycle.py
python3 -m pytest -q tests/test_promptbranch_mvp_proof.py tests/test_promptbranch_cli.py tests/test_project_control_surface.py
python3 scripts/run-release-validation-groups.py --repo . --json
python3 -m compileall -q .
python3 promptbranch_artifact_guardian.py \
  --repo . \
  --zip chatgpt_claudecode_workflow-2_v0.1.123.1.zip \
  --version v0.1.123.1 \
  --json
```

## Candidate validation completed

```text
Mandatory deterministic groups: 16/16 passed individually
Integrated MVP lifecycle tests:  5 passed
Release-pipeline group:           53 passed
Project control surface:          25 passed
Authority/behavioral surface:     20 passed
Application architecture:         43 passed
Artifact JSON contracts:          48 passed
Repository/project registry:      26 passed
Release-set planner:              17 passed
Release-set rollout/recovery:     12 passed
Sandbox rollback gate:            13/13 passed
Execution-envelope gate:          passed
Bash syntax:                      passed
Compileall:                        passed
```
