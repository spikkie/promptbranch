# Release v0.1.0 — JSON Orchestration State MVP foundation

## Input baseline

```text
chatgpt_claudecode_workflow_v0.0.278.86.zip
```

## Branch

```text
mvp/json-orchestration-state-v0.1.0
```

## Summary

This release opens the v0.1.x JSON Orchestration State MVP line from the current evolved main baseline.

It adds global and detailed planning documentation, high-level and low-level canvases, JSON orchestration schemas/examples, a k8s-game MVP state machine, provider policy, and architecture decisions.

## Added

```text
orchestration/README.md
orchestration/docs/global_mvp_plan.md
orchestration/docs/detailed_mvp_setup_plan.md
orchestration/docs/json_orchestration_state_mvp.md
orchestration/docs/json_orchestration_state_mvp_v0_1_0_high_level_canvas.md
orchestration/docs/json_orchestration_state_mvp_v0_1_0_low_level_canvas.md
orchestration/docs/k8s_game_mvp_contract.md
orchestration/docs/llm_provider_policy.md
orchestration/docs/proposal_vs_accepted_event.md
orchestration/docs/branching_strategy.md
orchestration/decisions/ADR-0001-json-orchestration-state-mvp.md
orchestration/decisions/ADR-0002-chatgpt-proposal-vs-promptbranch-accepted-event.md
orchestration/decisions/ADR-0003-chatgpt-only-llm-provider.md
orchestration/decisions/ADR-0004-ollama-bakeoff-failed-threshold.md
orchestration/schemas/context.schema.json
orchestration/schemas/decision.schema.json
orchestration/schemas/evidence.schema.json
orchestration/examples/k8s_game_context.example.json
orchestration/examples/k8s_game_decision.example.json
orchestration/examples/k8s_game_evidence.example.json
orchestration/state_machines/k8s_game_mvp.state_machine.json
scripts/orchestration/validate_examples.py
tests/orchestration/test_orchestration_examples.py
```

## Provider decision

```text
ChatGPT is the only critical-path LLM provider.
Ollama is excluded from v0.1.1 based on larger-model bakeoff failure.
```

## Non-goals

```text
- no game implementation
- no Kubernetes deployment
- no write-capable orchestration
- no runtime orchestration engine
- no Ollama provider or fallback
- no artifact adoption from model output
```

## Validation

Expected validation:

```bash
python3 scripts/orchestration/validate_examples.py
python3 -m pytest -q tests/orchestration/test_orchestration_examples.py
python3 -m compileall -q .
```

## Next release

```text
v0.1.1 — promptbranch.orchestration.grill schema and read-only ChatGPT-provider validation.
```
