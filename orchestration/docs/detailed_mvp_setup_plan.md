# JSON Orchestration State MVP — Detailed Planning Checklist

## Baseline

```text
input baseline: chatgpt_claudecode_workflow_v0.0.278.86.zip
target version: v0.1.0
branch: mvp/json-orchestration-state-v0.1.0
release type: normal minor-version MVP foundation release
```

## v0.1.0 detailed tasks

### 1. Version surfaces

```text
VERSION -> v0.1.0
pyproject.toml -> 0.1.0
promptbranch_version.py -> 0.1.0
```

### 2. Foundation docs

```text
orchestration/README.md
orchestration/docs/global_mvp_plan.md
orchestration/docs/detailed_mvp_setup_plan.md
orchestration/docs/json_orchestration_state_mvp.md
orchestration/docs/json_orchestration_state_mvp_v0_1_0_high_level_canvas.md
orchestration/docs/json_orchestration_state_mvp_v0_1_0_low_level_canvas.md
orchestration/docs/k8s_game_mvp_contract.md
orchestration/docs/proposal_vs_accepted_event.md
orchestration/docs/branching_strategy.md
orchestration/docs/llm_provider_policy.md
```

### 3. Architecture decisions

```text
orchestration/decisions/ADR-0001-json-orchestration-state-mvp.md
orchestration/decisions/ADR-0002-chatgpt-proposal-vs-promptbranch-accepted-event.md
orchestration/decisions/ADR-0003-chatgpt-only-llm-provider.md
orchestration/decisions/ADR-0004-ollama-bakeoff-failed-threshold.md
```

### 4. Data surfaces

```text
orchestration/schemas/context.schema.json
orchestration/schemas/decision.schema.json
orchestration/schemas/evidence.schema.json
orchestration/examples/k8s_game_context.example.json
orchestration/examples/k8s_game_decision.example.json
orchestration/examples/k8s_game_evidence.example.json
orchestration/state_machines/k8s_game_mvp.state_machine.json
```

### 5. Read-only validation fixture

```text
scripts/orchestration/validate_examples.py
tests/orchestration/test_orchestration_examples.py
```

This validation is intentionally small and read-only.

### 6. Release docs

```text
docs/release-v0.1.0.md
```

## v0.1.0 validation checklist

```bash
python3 scripts/orchestration/validate_examples.py
python3 -m pytest -q tests/orchestration/test_orchestration_examples.py
python3 -m compileall -q .
```

Optional adjacent Promptbranch checks:

```bash
python3 -m pytest -q tests/test_promptbranch_cli.py -k "candidate_next or mvp_status or artifact_current"
python3 -m pytest -q tests/test_promptbranch_cli.py -k "release_doctor or release_lifecycle"
```

## v0.1.1 detailed handoff

v0.1.1 adds `promptbranch.orchestration.grill`.

Planned files:

```text
orchestration/schemas/grill.schema.json
orchestration/examples/grills/G0_intent_grill.example.json
orchestration/examples/grills/G1_mvp_grill.example.json
orchestration/examples/grills/G2_architecture_grill.example.json
orchestration/examples/grills/G3_slice_grill.example.json
orchestration/examples/grills/G4_implementation_grill.example.json
orchestration/examples/grills/G5_release_deployment_grill.example.json
orchestration/examples/grills/G6_maintenance_grill.example.json
scripts/orchestration/validate_grill.py
tests/orchestration/test_orchestration_grill_schema.py
tests/orchestration/test_orchestration_grill_provider_policy.py
docs/release-v0.1.1.md
```

Provider policy in v0.1.1:

```text
allowed: chatgpt
allowed for test fixtures only: manual_fixture
rejected: ollama, local_llm, unknown
```

## Exit criteria for the planning MVP

The planning MVP is ready for implementation slices when:

```text
- v0.1.0 is adopted as current artifact/source baseline.
- v0.1.1 validates G0-G6 grill envelopes read-only.
- provider.kind=ollama is rejected in tests.
- model_may_execute=true is rejected in tests.
- promptbranch_must_validate=false is rejected in tests.
```
