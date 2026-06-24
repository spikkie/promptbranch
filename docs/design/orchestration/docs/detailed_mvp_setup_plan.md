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
docs/design/orchestration/README.md
docs/design/orchestration/docs/global_mvp_plan.md
docs/design/orchestration/docs/detailed_mvp_setup_plan.md
docs/design/orchestration/docs/json_orchestration_state_mvp.md
docs/design/orchestration/docs/json_orchestration_state_mvp_v0_1_0_high_level_canvas.md
docs/design/orchestration/docs/json_orchestration_state_mvp_v0_1_0_low_level_canvas.md
docs/design/orchestration/docs/k8s_game_mvp_contract.md
docs/design/orchestration/docs/proposal_vs_accepted_event.md
docs/design/orchestration/docs/branching_strategy.md
docs/design/orchestration/docs/llm_provider_policy.md
```

### 3. Architecture decisions

```text
docs/design/orchestration/decisions/ADR-0001-json-orchestration-state-mvp.md
docs/design/orchestration/decisions/ADR-0002-chatgpt-proposal-vs-promptbranch-accepted-event.md
docs/design/orchestration/decisions/ADR-0003-chatgpt-only-llm-provider.md
docs/design/orchestration/decisions/ADR-0004-ollama-bakeoff-failed-threshold.md
```

### 4. Data surfaces

```text
docs/design/orchestration/schemas/context.schema.json
docs/design/orchestration/schemas/decision.schema.json
docs/design/orchestration/schemas/evidence.schema.json
docs/design/orchestration/examples/k8s_game_context.example.json
docs/design/orchestration/examples/k8s_game_decision.example.json
docs/design/orchestration/examples/k8s_game_evidence.example.json
docs/design/orchestration/state_machines/k8s_game_mvp.state_machine.json
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
docs/design/orchestration/schemas/grill.schema.json
docs/design/orchestration/examples/grills/G0_intent_grill.example.json
docs/design/orchestration/examples/grills/G1_mvp_grill.example.json
docs/design/orchestration/examples/grills/G2_architecture_grill.example.json
docs/design/orchestration/examples/grills/G3_slice_grill.example.json
docs/design/orchestration/examples/grills/G4_implementation_grill.example.json
docs/design/orchestration/examples/grills/G5_release_deployment_grill.example.json
docs/design/orchestration/examples/grills/G6_maintenance_grill.example.json
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


## v0.1.40 reconciliation and grill foundation

`v0.1.40` is the reconciled continuation of the original planned `v0.1.1` grill slice after the line absorbed operational hardening through `v0.1.39`.

Added files:

```text
docs/design/orchestration/docs/current_status.md
docs/design/orchestration/docs/release_line_reconciliation.md
docs/design/orchestration/schemas/grill.schema.json
docs/design/orchestration/examples/grills/G0_intent.example.json
docs/design/orchestration/examples/grills/G1_mvp.example.json
docs/design/orchestration/examples/grills/G2_architecture.example.json
docs/design/orchestration/examples/grills/G3_slice.example.json
docs/design/orchestration/examples/grills/G4_implementation.example.json
docs/design/orchestration/examples/grills/G5_release_deployment.example.json
docs/design/orchestration/examples/grills/G6_maintenance.example.json
scripts/orchestration/validate_grill.py
tests/orchestration/test_orchestration_grill_schema.py
docs/release-v0.1.40.md
```

Validation checklist:

```bash
python3 scripts/orchestration/validate_examples.py
python3 scripts/orchestration/validate_grill.py
python3 -m pytest -q tests/orchestration
python3 -m compileall -q .
```

Scope boundary:

```text
read-only validation only
no accepted-event write path
no source mutation
no artifact adoption
no Kubernetes deployment
no Ollama/local_llm provider approval
```

## Next handoff after v0.1.40

The next orchestration slice should map valid grill stages to allowed k8s-game state-machine transitions, still read-only.

## v0.1.86 detailed handoff

`v0.1.86` is a reconciliation-only slice from accepted/current `chatgpt_claudecode_workflow-2_v0.1.85.zip`.

Planned files updated by this slice:

```text
docs/project/mvp.md
docs/project/definition-of-done.md
docs/project/plan.md
docs/project/status.md
docs/project/release-status.md
docs/project/decisions.md
docs/project/migration.md
docs/design/orchestration/docs/current_status.md
docs/design/orchestration/docs/global_mvp_plan.md
docs/design/orchestration/docs/detailed_mvp_setup_plan.md
docs/design/orchestration/docs/k8s_game_mvp_contract.md
docs/release-v0.1.86.md
```

Validation checklist:

```bash
python3 -m pytest -q tests/test_project_control_surface.py tests/orchestration/test_orchestration_examples.py tests/test_promptbranch_version.py
python3 -m compileall -q promptbranch_cli.py promptbranch_state.py promptbranch_orchestration.py
python3 promptbranch_cli.py artifact guard --zip chatgpt_claudecode_workflow-2_v0.1.86.zip --version v0.1.86 --json
python3 promptbranch_cli.py artifact verify chatgpt_claudecode_workflow-2_v0.1.86.zip --json
```

Scope boundary:

```text
read-only documentation/control-surface reconciliation only
no game implementation
no Docker build or image publication
no Kubernetes manifest application
no kubectl/Helm cluster mutation
no accepted-event ledger write
no Project Source mutation
no artifact adoption/current behavior change
```

## Next handoff after v0.1.86

The next game-related slice may create a static-app scaffold as repository files only. It must not deploy to Kubernetes until a later accepted dry-run/deploy evidence gate exists.
