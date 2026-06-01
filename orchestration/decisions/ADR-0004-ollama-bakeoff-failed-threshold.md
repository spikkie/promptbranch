# ADR-0004 — Ollama Bakeoff Failed Threshold

## Status

Accepted for v0.1.1 scope.

## Decision

Exclude Ollama from the v0.1.1 critical orchestration/grilling path.

## Evidence

The local larger-model Ollama bakeoff reported:

```text
FAIL: no model met the configured threshold.
```

## Consequences

No Ollama provider, fallback, voting, baseline selection, release approval, or tool execution is allowed in v0.1.1.

Future reintroduction requires a passing bakeoff and a new ADR.
