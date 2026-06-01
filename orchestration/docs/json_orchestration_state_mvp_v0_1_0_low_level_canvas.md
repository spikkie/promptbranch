# JSON Orchestration State MVP — v0.1.0 Low-Level Canvas

## 1. Document purpose

This is the detailed setup plan for the new MVP line:

```text
JSON Orchestration State MVP foundation
version: v0.1.0
baseline: chatgpt_claudecode_workflow_v0.0.278.86.zip
branch: mvp/json-orchestration-state-v0.1.0
```

The high-level canvas explains the idea and architecture. This low-level canvas explains exactly how to set up the MVP in the repository without overbuilding it.

## 2. Lowy-inspired setup principle

Use the Lowy-inspired architecture discipline as a control-surface discipline, not as a full heavyweight framework in the first slice.

Core doctrine:

```text
System = set of invariants
Slices = groups of invariants
Contracts = carriers of invariants
Code = enforcement of invariants
Tests = proof of invariants
Process = mechanism to evolve invariants safely
```

For v0.1.0 this means:

```text
No runtime orchestration engine yet.
No game implementation yet.
No write-capable agent yet.
No local Ollama critical-path provider.

Only:
- control surfaces
- schemas
- one state machine
- one project contract
- examples
- global and detailed planning docs
- proof tests if small enough
- grilling-loop documentation
```

## 3. Hard scope boundary

### In scope for v0.1.0

```text
- branch strategy document
- orchestration architecture document
- global MVP plan
- detailed MVP setup plan
- k8s-game-mvp contract document
- context JSON schema
- decision JSON schema
- evidence JSON schema
- k8s-game-mvp state-machine JSON
- example context JSON
- example decision JSON
- example evidence JSON
- proposal-vs-accepted-event document
- high-level canvas
- low-level canvas
- G0-G6 grilling-loop model
- ChatGPT-only provider decision for v0.1.1
- release note
- optional schema fixture tests
```

### Out of scope for v0.1.0

```text
- game source code
- Dockerfile for the game
- Kubernetes manifests for the game
- deployment workflow
- runtime orchestration CLI command
- artifact intake changes
- source sync changes
- write tools
- model-driven execution
- generic workflow engine
- Ollama provider or fallback
- multi-model voting
```

## 4. Repository layout

v0.1.0 should add this documentation/data-surface layout:

```text
orchestration/
  README.md
  docs/
    branching_strategy.md
    global_mvp_plan.md
    detailed_mvp_setup_plan.md
    json_orchestration_state_mvp.md
    json_orchestration_state_mvp_v0_1_0_high_level_canvas.md
    json_orchestration_state_mvp_v0_1_0_low_level_canvas.md
    k8s_game_mvp_contract.md
    llm_provider_policy.md
    proposal_vs_accepted_event.md
  decisions/
    ADR-0001-json-orchestration-state-mvp.md
    ADR-0002-chatgpt-proposal-vs-promptbranch-accepted-event.md
    ADR-0003-chatgpt-only-llm-provider.md
    ADR-0004-ollama-bakeoff-failed-threshold.md
  schemas/
    context.schema.json
    decision.schema.json
    evidence.schema.json
  examples/
    k8s_game_context.example.json
    k8s_game_decision.example.json
    k8s_game_evidence.example.json
  state_machines/
    k8s_game_mvp.state_machine.json
scripts/
  orchestration/
    validate_examples.py
tests/
  orchestration/
    test_orchestration_examples.py
docs/
  release-v0.1.0.md
```

## 5. Setup sequence

### Step 0 — Confirm current main baseline

```bash
pb artifact current --json | python3 -m json.tool
pb artifact candidate-next --json | python3 -m json.tool
cat VERSION
```

Expected:

```text
v0.0.278.86 is the current main source/artifact baseline.
candidate-next has no actionable stale candidate.
```

### Step 1 — Create branch

```bash
git switch main
git pull --ff-only
git switch -c mvp/json-orchestration-state-v0.1.0
```

### Step 2 — Bump version

Update:

```text
VERSION: v0.1.0
pyproject.toml: 0.1.0
promptbranch_version.py: 0.1.0
```

### Step 3 — Add orchestration planning/data surfaces

Add:

```text
high-level canvas
low-level canvas
global MVP plan
detailed MVP setup plan
schemas
examples
state machine
branching strategy
provider policy
ADRs
release note
```

### Step 4 — Add read-only example validation

Add only a small fixture validator for examples/state machine consistency.

Do not implement full `promptbranch.orchestration.grill` runtime validation in v0.1.0. That belongs to v0.1.1.

### Step 5 — Run focused checks

```bash
python3 scripts/orchestration/validate_examples.py
python3 -m pytest -q tests/orchestration/test_orchestration_examples.py
python3 -m compileall -q .
```

Optional adjacent checks:

```bash
python3 -m pytest -q tests/test_promptbranch_cli.py -k "candidate_next or mvp_status or artifact_current"
python3 -m pytest -q tests/test_promptbranch_cli.py -k "release_doctor or release_lifecycle"
```

### Step 6 — Package ZIP

Create:

```text
chatgpt_claudecode_workflow_v0.1.0.zip
```

ZIP requirements:

```text
- root opens directly to repo contents
- VERSION exists at root
- VERSION == v0.1.0
- no wrapper folder
- no nested ZIPs
- no .pb_profile
- no __pycache__
- no .pytest_cache
- no .venv
- no node_modules
- no local secrets
```

## 6. v0.1.1 handoff

v0.1.0 intentionally hands off to v0.1.1.

v0.1.1 scope:

```text
ChatGPT-only promptbranch.orchestration.grill validation slice.
```

v0.1.1 should add:

```text
- grill.schema.json
- G0-G6 grill examples
- read-only validate_grill.py
- provider policy validation
- tests rejecting provider.kind=ollama
```

v0.1.1 must not add:

```text
- Ollama provider implementation
- local LLM fallback
- multi-model voting
- write-capable orchestration
- artifact adoption from grill output
```

## 7. Definition of done

```text
[ ] Branch created from main at v0.0.278.86.
[ ] VERSION is v0.1.0.
[ ] pyproject is 0.1.0.
[ ] Global MVP plan exists.
[ ] Detailed MVP setup plan exists.
[ ] High-level canvas exists.
[ ] Low-level canvas exists.
[ ] Context/decision/evidence schemas exist.
[ ] Context/decision/evidence examples exist.
[ ] K8s game state machine exists.
[ ] K8s game MVP contract exists.
[ ] Proposal-vs-accepted-event doc exists.
[ ] ChatGPT-only LLM provider policy exists.
[ ] Ollama bakeoff failure/exclusion ADR exists.
[ ] Example validation passes.
[ ] ZIP hygiene passes.
[ ] No game/deployment/write-agent code is included.
```

## 8. Final verdict

Correct v0.1.0 shape:

```text
planning + schemas + examples + state machine + provider decision + release note
```

Incorrect v0.1.0 shape:

```text
generic workflow engine + game implementation + deployment + Ollama provider + write tools
```
