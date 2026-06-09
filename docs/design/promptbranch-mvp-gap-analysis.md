# Promptbranch MVP Gap Analysis

Release: `v0.1.60`
Baseline: `chatgpt_claudecode_workflow-2_v0.1.58.zip`
Status: PB application design docs-status / diagram-freshness guard

## Purpose

This document records the current gap between the living design, the consolidated orchestration design/control surfaces, and the implementation baseline accepted at `v0.1.58`. It is intentionally a design/control document; it does not introduce runtime orchestration behavior.

## Current accepted baseline

```text
accepted baseline: chatgpt_claudecode_workflow-2_v0.1.58.zip
runtime/source/artifact/registry: v0.1.58 accepted baseline
full-test evidence: deferred for narrow documentation/validation slice
next normal release: v0.1.60
```

## Consolidation decision

The root-level `orchestration/` tree contained MVP design/control surfaces, not runtime code. v0.1.54 moves those surfaces to:

```text
docs/design/orchestration/
```

This makes `docs/design/` the canonical home for active architecture/design material while preserving `scripts/orchestration/` and `tests/orchestration/` as executable validation surfaces.

## Implemented / proven

- `v0.1.58` is accepted and baseline-current verified after the PB application design documentation and diagram release.
- Backend diagnostics are integrated.
- Source overwrite/profile-lock concurrency is fixed enough to pass full release-control.
- Docker Compose service image tagging no longer hardcodes the release version; release scripts derive image metadata from `VERSION`.
- Read-only orchestration context/decision/evidence validation exists.
- Read-only grill envelope validation exists with ChatGPT/manual-fixture provider policy and Ollama rejection.
- Read-only grill validation now checks k8s-game MVP state-machine project identity and stage-specific transition recommendations.
- Read-only accepted-event validation now consumes committed valid grill fixtures for G0-G6, verifies each source hash, and proves each accepted transition matches both the source recommendation and the state machine.
- Living-design docs-status validation exists.
- `v0.1.58` adds `docs/design/promptbranch-application-design.md` and extends the existing draw.io sources with activity, data-flow, state-transition, role-component, and release-state pages.
- `v0.1.59` extends docs-status so those PB application design surfaces are blocked if missing, unreferenced, not parseable, or missing required role/scope/freshness language.

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

After v0.1.59 is accepted, choose one narrow slice:

1. Add rejected-event fixtures that prove invalid grill recommendations cannot become trusted workflow state.
2. Extend docs-status further so it also checks accepted-event fixture coverage and source-grill hash freshness.
3. Add a read-only status/checkpoint command for accepted-event coverage completeness.

Do not start game implementation or write-capable orchestration until the design/control surfaces remain stable after the state-machine transition validation slice.

## v0.1.60 update

`v0.1.60` closes an operational evidence gap: it documents and validates the distinction between a generated/transient candidate ZIP and the locally accepted Promptbranch artifact. After adoption, the accepted artifact reported by `pb artifact current --json` / `pb release baseline-status --json` is authoritative for continuation.
