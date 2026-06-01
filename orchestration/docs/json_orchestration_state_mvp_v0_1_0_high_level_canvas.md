# JSON Orchestration State MVP — v0.1.0 High-Level Canvas

## 1. MVP identity

```text
name: JSON Orchestration State MVP foundation
version: v0.1.0
baseline: chatgpt_claudecode_workflow_v0.0.278.86.zip
branch: mvp/json-orchestration-state-v0.1.0
stable branch: main at chatgpt_claudecode_workflow_v0.0.278.86.zip
primary test vehicle: k8s-game-mvp
next planned release: v0.1.1 formalizes promptbranch.orchestration.grill
```

This release starts a new minor-version MVP line from the current evolved main baseline. Older prototype artifacts built from v0.0.276.1 are superseded as baselines and may be used only as planning donors.

## 2. Core architecture

The JSON Orchestration State MVP must not make an LLM the orchestrator.

The correct architecture is:

```text
ChatGPT = deliberation and grilling engine
JSON = typed proposal/event/evidence contract
Promptbranch = deterministic control-plane state machine
Final Artifact Intake MVP = release artifact ingress/adoption gate
Tools/tests/deployment = evidence producers
```

One-sentence rule:

```text
ChatGPT proposes and grills; Promptbranch validates and records; tools produce evidence; Artifact Intake accepts only verified release artifacts.
```

## 3. LLM provider decision

The JSON Orchestration State MVP uses **ChatGPT as the only LLM provider in the critical orchestration/grilling path**.

Local Ollama is excluded from the critical path for v0.1.1.

Reason:

```text
The larger-model Ollama bakeoff did not meet the configured validation threshold.
```

Architecture consequence:

```text
ChatGPT = primary and only LLM reasoning/grilling provider for v0.1.1
Promptbranch = schema, policy, state-machine, artifact, and release authority
Ollama = excluded from critical orchestration/grilling path
```

Allowed in v0.1.1:

```text
ChatGPT-produced promptbranch.orchestration.grill proposals
Promptbranch read-only validation
Promptbranch accepted/rejected event classification
```

Not allowed in v0.1.1:

```text
Ollama grill provider
Ollama fallback provider
multi-model decision voting
local LLM baseline selection
local LLM release approval
local LLM tool execution
```

Future local models are not permanently forbidden, but they require a passing bakeoff and a new ADR before reintroduction.

## 4. Why grilling matters

Grilling is the adversarial review activity that prevents vague ideas from becoming uncontrolled implementation.

It should not be a single early stage. It returns at major boundaries:

```text
Grilling -> Architecture -> Grilling -> Slice -> Grilling -> Code -> Grilling -> Release -> Grilling -> Deployment -> Grilling -> Maintenance
```

Grilling is proportional to risk. It should be strict at architecture, slice, release, and deployment boundaries, but it must not block every tiny local edit.

## 5. Grilling principle

Grilling has five jobs:

```text
1. Expose hidden assumptions.
2. Shrink scope to the smallest valid proof.
3. Convert vague intent into testable boundaries and evidence requirements.
4. Identify forbidden capabilities before implementation.
5. Require evidence before release, deployment, and maintenance transitions.
```

Grilling is not authority.

```text
ChatGPT grill result = untrusted proposal
Promptbranch accepted event = trusted workflow state after validation
```

## 6. Full grilling loop

```text
G0 — Intent grill
  ↓
G1 — MVP grill
  ↓
G2 — Architecture grill
  ↓
G3 — Slice grill
  ↓
G4 — Implementation grill
  ↓
G5 — Release/deployment grill
  ↓
G6 — Maintenance grill
```

Each grilling session has a different input set, purpose, and output.

## 7. G0 — Intent grill

Purpose: decide whether the raw idea is worth shaping into an MVP.

Input:

```text
raw idea
goal
target user/operator
constraints
non-goals
success signal
what must not happen
```

Output:

```text
accepted/rejected idea
```

For k8s-game-mvp, the idea is accepted only if the game remains a controlled orchestration test vehicle, not a game product.

## 8. G1 — MVP grill

Purpose: define the smallest MVP that proves the thesis.

Input:

```text
proof target
baseline
version line
smallest deliverable
allowed tech stack
excluded capabilities
```

Output:

```text
MVP contract
```

For v0.1.0, the accepted MVP is:

```text
schemas + examples + state machine + k8s-game contract + global/detailed planning docs
```

Rejected for v0.1.0:

```text
game implementation
deployment
write-capable orchestration
generic orchestration engine
```

## 9. G2 — Architecture grill

Purpose: challenge the proposed architecture before implementation.

Input:

```text
boundaries
state
trust model
artifacts
evidence
current baseline
expected next release
```

Output:

```text
architecture decision
```

Accepted architecture:

```text
ChatGPT = deliberation engine
Promptbranch = control-plane state machine
Artifact Intake = release artifact ingestion gate
JSON = typed event contract
```

Rejected architecture:

```text
ChatGPT as orchestrator
local Ollama as trusted planner
generic workflow engine in v0.1.0
```

## 10. G3 — Slice grill

Purpose: prevent the next slice from becoming too broad.

Input:

```text
current state
target state
allowed files
forbidden files
expected tests/evidence
release type
```

Output:

```text
slice contract
```

For v0.1.0, the correct slice type is:

```text
boundary/data-surface/documentation-planning slice
```

## 11. G4 — Implementation grill

Purpose: review changed files before packaging.

Input:

```text
changed files
tests
version surfaces
schemas/examples
release notes
known non-goals
```

Output:

```text
implementation review
```

For v0.1.0, implementation grilling must reject game code, deployment code, write-capable agents, and runtime orchestration behavior.

## 12. G5 — Release/deployment grill

Purpose: prevent false acceptance and unsafe deployment.

Release input:

```text
ZIP
validation output
Artifact Intake result
finalizer output
candidate-next result
```

Release output:

```text
release decision
```

Deployment input:

```text
manifests
namespace
ingress or port-forward path
rollout status
smoke result
```

Deployment output:

```text
deployment evidence
```

For v0.1.0, deployment grilling is documented only. Deployment belongs to a later v0.1.x release.

## 13. G6 — Maintenance grill

Purpose: learn from the accepted release and choose the next risk-controlled slice.

Input:

```text
accepted baseline
weaknesses
failed assumptions
next risk
candidate-next status
current branch
```

Output:

```text
next slice recommendation
```

For v0.1.0, expected recommendation:

```text
v0.1.1 — add promptbranch.orchestration.grill schema, G0-G6 examples, ChatGPT-only provider policy, and read-only validation
```

## 14. Input model by scope

| Scope | Input needed | Output |
|---|---|---|
| Intent | raw idea, goal, user, constraints, non-goals | accepted/rejected idea |
| MVP | proof target, baseline, version line, smallest deliverable | MVP contract |
| Architecture | boundaries, state, trust model, artifacts, evidence | architecture decision |
| Slice | current state, target state, allowed/forbidden files | slice contract |
| Implementation | changed files, tests, version surfaces | implementation review |
| Release | ZIP, validation, intake/finalizer output | release decision |
| Deployment | manifests, namespace, ingress/port-forward, smoke result | deployment evidence |
| Maintenance | accepted baseline, weaknesses, next risk | next slice recommendation |

## 15. v0.1.1 scope: promptbranch.orchestration.grill

v0.1.1 should introduce a dedicated envelope and keep ChatGPT as the only critical-path LLM provider:

```text
promptbranch.orchestration.grill
```

Provider rule for v0.1.1:

```text
provider.kind = chatgpt
provider.role = primary_grill
```

The validator should be read-only, should not depend on Ollama, and should not invoke any local LLM.

v0.1.1 validates:

```text
schema identity is promptbranch.orchestration.grill
grill_id is one of G0..G6
scope/stage match grill_id
decision is allowed
provider.kind is chatgpt or manual_fixture in test mode
provider.kind=ollama is rejected
model_may_execute=false
promptbranch_must_validate=true
next_stage does not skip the state machine
```

## 16. Release progression

```text
v0.1.0
  Foundation: global/detailed planning docs, schemas, examples, state machine, k8s-game contract, grilling loop documented.

v0.1.1
  Add promptbranch.orchestration.grill schema and read-only validation.
  ChatGPT is the only critical-path LLM provider.
  Ollama is excluded from orchestration/grilling based on bakeoff failure.

v0.1.2
  Add explicit k8s-game grill examples for G0-G3.
  Provider remains ChatGPT-only unless a future ADR changes this.

v0.1.3
  Use the grilling loop before generating the first k8s-game implementation candidate.
```

## 17. Final verdict

Correct role:

```text
Grilling = adversarial review activity
Decision = machine-readable proposed outcome
Accepted event = Promptbranch-validated workflow state
```

Incorrect role:

```text
Grilling = orchestrator
Grilling = implementation authority
Grilling = mandatory ceremony for every tiny change
```

The correct next step is to keep v0.1.0 as a documentation/planning foundation and make v0.1.1 the first release that formalizes grilling as `promptbranch.orchestration.grill` with ChatGPT as the only critical-path LLM provider.
