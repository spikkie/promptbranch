# Release v0.1.76

## Slice

KISS repo-loop consumer cleanup for operator scripts and release-state checks.

## Baseline

```text
chatgpt_claudecode_workflow-2_v0.1.75.zip
```

## Goal

Remove remaining old single-repo `pb artifact current --json` consumer assumptions from operator/release scripts and release-state checks.

## Summary

`v0.1.75` made the artifact-current producer use one repo-loop model for one repo or many repos. `v0.1.76` continues that KISS line by updating downstream consumers so they also read `repos[repo_id]` entries instead of top-level `state` and `registry_current` fields.

## In scope

- `chatgpt_claudecode_workflow_release_control.sh` artifact-current semantic verification.
- `scripts/post-release-validation.sh` pre-adoption, post-adoption, lifecycle-status, and human-summary artifact-current checks.
- Focused tests/static guards proving release/operator consumers use repo-loop entries.
- CLI compatibility helper for selecting artifact-current repo entries from repo-loop payloads, with legacy parsing kept only as compatibility fallback.
- Project status, DoD, release-status, decisions, and version metadata.

## Out of scope

- New multi-repo orchestration behavior.
- Dependency solving between repositories.
- Automatic cross-repo adoption.
- Artifact registry storage format changes.
- Project Source upload behavior changes.
- Browser automation behavior changes.
- Docker/deployment behavior changes.

## Validation

```text
focused artifact/current regression tests: passed
project/repo/control/version tests: passed
release-control/post-release semantic guard tests: passed
bash syntax checks: passed
compileall: passed
```

## Acceptance

Candidate until full release-control and adoption/current evidence confirm alignment.
