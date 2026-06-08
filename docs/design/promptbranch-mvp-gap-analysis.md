# Promptbranch MVP Gap Analysis

Release: `v0.1.55`
Baseline: `chatgpt_claudecode_workflow-2_v0.1.54.1.zip`
Status: read-only grill/state-machine transition validation

## Purpose

This document records the current gap between the living design, the consolidated orchestration design/control surfaces, and the implementation baseline assumed accepted at `v0.1.54.1`. It is intentionally a design/control document; it does not introduce runtime orchestration behavior.

## Current accepted baseline

```text
accepted baseline: chatgpt_claudecode_workflow-2_v0.1.54.1.zip
runtime/source/artifact/registry: v0.1.54.1 assumed from accepted repair
full-test evidence: deferred for narrow development slice
next normal release: v0.1.55
```

## Consolidation decision

The root-level `orchestration/` tree contained MVP design/control surfaces, not runtime code. v0.1.54 moves those surfaces to:

```text
docs/design/orchestration/
```

This makes `docs/design/` the canonical home for active architecture/design material while preserving `scripts/orchestration/` and `tests/orchestration/` as executable validation surfaces.

## Implemented / proven

- `v0.1.53` was accepted and baseline-current verified; `v0.1.54.1` is the assumed current repair baseline for this normal continuation slice.
- Backend diagnostics are integrated.
- Source overwrite/profile-lock concurrency is fixed enough to pass full release-control.
- Docker Compose service image tagging no longer hardcodes the release version; release scripts derive image metadata from `VERSION`.
- Read-only orchestration context/decision/evidence validation exists.
- Read-only grill envelope validation exists with ChatGPT/manual-fixture provider policy and Ollama rejection.
- Read-only grill validation now checks k8s-game MVP state-machine project identity and stage-specific transition recommendations.
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

After v0.1.55 is accepted, choose one narrow slice:

1. Add more schema-backed G0-G6 grill fixtures under `docs/design/orchestration/examples/`.
2. Add a separate accepted-event fixture/validator that consumes a valid grill recommendation without mutating runtime state.
3. Extend docs-status so it also checks the consolidated orchestration design root and grill/state-machine transition coverage.

Do not start game implementation or write-capable orchestration until the design/control surfaces remain stable after the state-machine transition validation slice.
