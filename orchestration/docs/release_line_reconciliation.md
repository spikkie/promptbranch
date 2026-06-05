# JSON Orchestration State MVP — Release Line Reconciliation

## Problem

The original `orchestration/docs/global_mvp_plan.md` planned the early `v0.1.x` line as:

```text
v0.1.0  foundation docs/data surfaces
v0.1.1  grill schema and G0-G6 validation
v0.1.2  k8s-game grill fixtures
v0.1.3  implementation candidate planning
v0.1.4  deployment evidence loop
```

The actual line reached `v0.1.39` before the grill schema was added.

## Finding

This is acceptable only if the intervening work is treated as control-plane hardening, not a replacement for the orchestration MVP.

The important hardening detours were:

```text
release-control/adoption reliability
source/artifact handling reliability
task/message and answer handling reliability
profile lease/pool support for live tests
rate-limit detection without bypassing service guardrails
backend API surface documentation
```

These support the goal because the orchestration MVP depends on reliable state, baseline, browser/profile, and rate-limit behavior.

## Correction in v0.1.40

This release performs two corrections:

```text
1. document the real line state after v0.1.39
2. implement the planned read-only grill schema foundation
```

It intentionally does not implement:

```text
- generic orchestration engine
- automatic source mutation
- automatic artifact adoption
- Kubernetes deployment
- model-executed tools
- Ollama/local LLM provider approval
```

## Continuity rule

Future orchestration releases should describe whether they are:

```text
orchestration-feature slice
control-plane-hardening slice
repair slice
```

A hardening slice is allowed only when it protects one of the core orchestration invariants:

```text
state correctness
baseline continuity
profile/test isolation
rate-limit safety
artifact intake safety
provider authority separation
```

## Resumed MVP path

The resumed path is:

```text
v0.1.40  docs reconciliation + read-only grill schema/examples/validator/tests
next      read-only grill-to-state-machine transition validation
later     k8s-game project-specific grill fixtures
later     implementation planning candidate envelopes
later     deployment evidence envelope validation
```
