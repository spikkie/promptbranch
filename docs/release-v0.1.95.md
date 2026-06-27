# Release v0.1.95 — Controlled read-only loop execution evidence report

## Type

Normal MVP-1 slice.

## Baseline

`chatgpt_claudecode_workflow-2_v0.1.94.1.zip` accepted/current.

## Goal

Make the first controlled read-only loop execution step easier to verify by producing an explicit evidence report for path-scope inspection, declared validation commands, skipped command execution, and no-side-effect safety assertions.

## Implemented scope

- `pb loop run --read-only-execution` now embeds `evidence_report` in JSON output.
- `pb loop run --read-only-execution --evidence-report` emits the compact evidence report directly.
- The report uses schema `promptbranch.loop.read_only_evidence_report` version `1.0`.
- The report summarizes safe/unsafe path scope, matched path count, declared validation commands, skipped commands, and zero commands executed.
- The report repeats explicit safety assertions: no file mutation, no deployment, no Kubernetes mutation, no Project Source mutation, no artifact adoption, and no ChatGPT Project deletion.

## Out of scope

- No command execution.
- No file mutation.
- No Kubernetes mutation or deployment.
- No Project Source mutation from loop execution.
- No artifact adoption from loop execution.
- No ChatGPT Project deletion behavior change.

## Validation

Focused validation covered loop evidence-report payload construction, CLI JSON/text behavior, mutual-exclusion/required-mode behavior, version surface, project control surface, compileall, Artifact Guardian, artifact verify, and ZIP hygiene.

Full release-control and adoption are not claimed by this document.
