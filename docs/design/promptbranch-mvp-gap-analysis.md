# Promptbranch MVP Gap Analysis

Release: `v0.1.56`
Baseline: `chatgpt_claudecode_workflow-2_v0.1.55.1.zip`
Status: read-only accepted-event fixture validation

## Purpose

This document records the current gap between the living design, the consolidated orchestration design/control surfaces, and the implementation baseline accepted at `v0.1.55.1`. It is intentionally a design/control document; it does not introduce runtime orchestration behavior.

## Current accepted baseline

```text
accepted baseline: chatgpt_claudecode_workflow-2_v0.1.55.1.zip
runtime/source/artifact/registry: v0.1.55.1 accepted repair baseline
full-test evidence: deferred for narrow read-only development slice
next normal release: v0.1.56
```

## Consolidation decision

The root-level `orchestration/` tree contained MVP design/control surfaces, not runtime code. v0.1.54 moves those surfaces to:

```text
docs/design/orchestration/
```

This makes `docs/design/` the canonical home for active architecture/design material while preserving `scripts/orchestration/` and `tests/orchestration/` as executable validation surfaces.

## Implemented / proven

- `v0.1.55.1` is accepted and baseline-current verified after the grill validator path-label repair.
- Backend diagnostics are integrated.
- Source overwrite/profile-lock concurrency is fixed enough to pass full release-control.
- Docker Compose service image tagging no longer hardcodes the release version; release scripts derive image metadata from `VERSION`.
- Read-only orchestration context/decision/evidence validation exists.
- Read-only grill envelope validation exists with ChatGPT/manual-fixture provider policy and Ollama rejection.
- Read-only grill validation now checks k8s-game MVP state-machine project identity and stage-specific transition recommendations.
- Read-only accepted-event validation now consumes a committed valid grill fixture, verifies its hash, and proves the accepted transition matches both the source recommendation and the state machine.
- Living-design docs-status validation exists.

## Partially implemented

- Ask/reply protocol and artifact intake are designed and partially implemented, but repeated real artifact roundtrip proof remains needed.
- Native release lifecycle has read-only/status surfaces and repo-local release-control remains the operational path.
- MCP/local agent flows are read-only and useful for inspection, but not a write-capable orchestration engine.

## Deferred / explicitly not implemented

- Generic orchestration runtime engine.
- Kubernetes game implementation.
- Deployment automation for the k8s game.
- Write-capable model or agent execution.
- Ollama as a critical-path orchestration/grilling provider.
- Model-driven artifact adoption.

## Next safe slice options

After v0.1.56 is accepted, choose one narrow slice:

1. Add accepted-event fixtures for the remaining G1-G6 grill stages.
2. Add rejected-event fixtures that prove invalid grill recommendations cannot become trusted workflow state.
3. Extend docs-status so it also checks accepted-event fixture coverage and source-grill hash freshness.

Do not start game implementation or write-capable orchestration until the design/control surfaces remain stable after the state-machine transition validation slice.
