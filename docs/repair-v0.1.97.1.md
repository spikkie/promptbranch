# Repair v0.1.97.1 — Text-source add post-commit reconciliation repair

## Base

- Base candidate: `chatgpt_claudecode_workflow-2_v0.1.97.zip`
- Accepted/current baseline before this repair line: `chatgpt_claudecode_workflow-2_v0.1.96.zip`
- Repair version: `v0.1.97.1`

## Reason

`v0.1.97` failed full release-control at `project_source_add_text` with `commit_seen_with_stale_inflight_not_verified_present`. The release ZIP source itself was visible in Project Source; the failed validation was the separate text-source add path.

## Change

The repair adds a post-commit text-source reconciliation path. After a text-source commit is observed and ordinary persistence proof times out, Promptbranch re-reads the Project Sources surface and accepts recovery only when exact text-source identity or content proof is visible. Nearby text sources and release ZIP source cards are rejected.

## No slice advancement

This repair preserves `v0.1.97 — Read-only loop evidence gate` behavior. It does not execute commands, mutate files, deploy, mutate Kubernetes, mutate Project Sources from loop execution, adopt artifacts from loop execution, or delete ChatGPT Projects.

## Validation

Focused validation covers:

- committed text source recovered after stale-inflight post-commit source-list reconciliation;
- nearby/different text source is not accepted;
- ZIP source visibility does not satisfy text-source validation;
- existing stale-inflight recovery and failure classification;
- version/control-surface checks.
