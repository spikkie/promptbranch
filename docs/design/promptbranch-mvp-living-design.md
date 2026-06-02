# Promptbranch MVP Living Design

Release: `v0.1.9`  
Status: source-of-truth design note plus editable draw.io source  
Related diagram: `docs/design/promptbranch-mvp-living-design.drawio`

## Purpose

This document explains the current Promptbranch MVP map, what has already been implemented, and what remains. It is intended to be updated after each MVP/release slice together with the editable draw.io source file.

The diagram is not a generated image. It is an editable `.drawio` source that can be opened in diagrams.net/draw.io and maintained as part of the repository.

## Important clarification: actual MVP

The actual current MVP is:

```text
json_orchestration_state_mvp
```

The living design document and diagram are not a competing MVP. They are the updateable visual/control-plane map around the actual MVP.

Read the actual MVP from these repo-relative sources:

- `orchestration/docs/json_orchestration_state_mvp.md`
- `orchestration/docs/json_orchestration_state_mvp_v0_1_0_high_level_canvas.md`
- `orchestration/docs/json_orchestration_state_mvp_v0_1_0_low_level_canvas.md`

Use the high-level canvas for the intent, architecture, and grilling model. Use the low-level canvas for the concrete repository layout, scope boundary, setup sequence, schemas, examples, tests, and release surfaces.

## Design center

Promptbranch is not trying to make ChatGPT.com literally become Claude Code. The target is a similar operating shape:

```text
Promptbranch CLI / local host = operator control plane
ChatGPT Project              = workspace
ChatGPT conversation         = task/session
Project Sources              = repo snapshots, specs, logs, source bundles
Generated ZIP artifacts      = release outputs
MCP tools                    = deterministic local capabilities
Skills                       = reusable operating procedures
Ollama                       = optional proposal/summarization only
```

For the actual `json_orchestration_state_mvp`, the critical rule is sharper:

```text
ChatGPT proposes and grills.
Promptbranch validates, records, and gates.
JSON carries typed state, proposals, decisions, and evidence.
Tools/tests/deployment produce evidence.
Artifact intake accepts only verified release artifacts.
```

The three Promptbranch operating scopes remain:

```text
Workspace = current ChatGPT Project
Task      = current chat/conversation inside that project
Artifact  = current repo/source bundle/release ZIP
```

The most important design invariant is that these scopes must be tracked independently. Runtime code can intentionally move ahead of the adopted Project Source baseline during focused development.

## Current MVP state

### Actual MVP surfaces

The actual MVP is represented by the orchestration source tree:

```text
orchestration/
  docs/
    json_orchestration_state_mvp.md
    json_orchestration_state_mvp_v0_1_0_high_level_canvas.md
    json_orchestration_state_mvp_v0_1_0_low_level_canvas.md
    global_mvp_plan.md
    detailed_mvp_setup_plan.md
    k8s_game_mvp_contract.md
    proposal_vs_accepted_event.md
    llm_provider_policy.md
  decisions/
  schemas/
  examples/
  state_machines/
```

The MVP thesis is:

```text
ChatGPT = deliberation and grilling engine
JSON = typed proposal/event/evidence contract
Promptbranch = deterministic control-plane state machine
Final Artifact Intake MVP = release artifact ingress/adoption gate
Tools/tests/deployment = evidence producers
```

### Already implemented or proven

- Canonical shell grammar is centered around `pb ws`, `pb task`, `pb src`, `pb artifact`, `pb test`, `pb debug`, `pb doctor`, `pb ask`, `pb agent`, `pb mcp`, and `pb skill`.
- Backend-first/read-only design exists for state, workspace, task, file, Git, artifact, and skill inspection paths.
- MCP server and stdio client paths exist for read-only local tools.
- Deterministic read-only agent paths exist for simple repository inspection.
- Skill registry and repo-inspection style skills exist for read-only guidance.
- `pb test smoke` provides a cheap regression gate.
- Ask/reply and artifact-intake design exists, including candidate-before-accepted-baseline semantics.
- Release doctor/config/install/lifecycle/checkpoint/docs-status commands now have read-only planning/diagnostic surfaces.
- CI-style development flow is explicit: focused development can continue across monotonic dev candidates while full release-control is deferred until the adoption checkpoint.
- Living design validation exists through `pb release docs-status --json`.

### Current development-line reality

The accepted baseline and development head may differ:

```text
accepted baseline: last full-test/adopted artifact from pb artifact current
development head:  latest monotonic candidate installed/tested with focused checks
```

That is intentional during development. It becomes a release problem only if adoption is attempted without full release-control and source/adopt verification.

## What we are trying to achieve

The actual MVP should produce a safe, typed orchestration loop:

```text
intent
  -> ChatGPT grill proposal
  -> Promptbranch schema/policy validation
  -> accepted or rejected JSON event
  -> evidence collection
  -> release artifact candidate
  -> artifact intake verification
  -> guarded adoption
  -> next task from known state
```

For local/tooling automation, the long-term architecture is:

```text
Promptbranch CLI
  -> deterministic planner / policy gate
  -> MCP client
  -> Promptbranch MCP server
  -> read-only tools first
  -> controlled process tools later
  -> transactional writes only after verification is solid
```

## Main tracks

| Track | Goal | Current state | Next movement |
|---|---|---|---|
| JSON orchestration state MVP | Actual MVP: typed proposal/event/evidence state | high/low-level canvases and orchestration surfaces exist | keep this as the central MVP in docs and diagrams |
| Grilling model | ChatGPT challenges intent/scope/evidence without becoming authority | G0-G6 model documented | add more schema-backed proof examples |
| Shell model | Stable workspace/task/artifact grammar | mostly established | continue documenting canonical forms |
| MCP/local agent | Promptbranch-native host/client/server loop | read-only paths exist | harden host-smoke/run/skill flows |
| Skills | Reusable local operating procedures | read-only skill registry exists | keep local-only until validation is stronger |
| Ask/reply protocol | Machine-readable ChatGPT replies | design and partial implementation exist | prove real artifact roundtrip end-to-end |
| Artifact intake | Candidate download/verify/migrate/adopt | mature but needs repeated live proof | guarded adoption from verified candidate |
| Native release lifecycle | Move repo-local lifecycle into Promptbranch | read-only doctor/config/install/lifecycle planning exists | controlled install/source/test/adopt in separate slices |
| CI-style dev flow | Focused tests during dev, full test at checkpoint | explicit dev-status/checkpoint commands exist | keep monotonic dev versions, no version rewrites |

## How to update the draw.io source

The draw.io page is deliberately split into stable update regions:

```text
1. Actual MVP identity
2. JSON orchestration control loop
3. Promptbranch operating shell
4. Evidence and artifact intake gate
5. Development/adoption flow
6. Documentation references
7. Update protocol
```

After each release slice:

1. Update the release/version marker in this document if the diagram meaning changed.
2. Update the draw.io page named `Promptbranch MVP Living Design`.
3. Keep `json_orchestration_state_mvp` visibly marked as the actual MVP unless the MVP line changes.
4. Keep the diagram source editable and avoid exporting static PNG/PDF unless explicitly requested.
5. Keep references repo-relative so links remain meaningful in ZIP releases.
6. Add newly completed commands or docs to the `Done / Current Surface` area.
7. Move next work from `Next / Planned` into `Done` only after focused tests or release-control evidence exists.
8. Run `pb release docs-status --json` after changing the Markdown or draw.io source.
9. Do not use the diagram as proof by itself; proof remains tests, release logs, schema validation, and validated JSON outputs.

## Referenced documentation

The draw.io source refers to these repo-relative documentation files:

- `docs/design/promptbranch-mvp-living-design.drawio`
- `orchestration/docs/json_orchestration_state_mvp.md`
- `orchestration/docs/json_orchestration_state_mvp_v0_1_0_high_level_canvas.md`
- `orchestration/docs/json_orchestration_state_mvp_v0_1_0_low_level_canvas.md`
- `orchestration/docs/global_mvp_plan.md`
- `orchestration/docs/detailed_mvp_setup_plan.md`
- `orchestration/docs/k8s_game_mvp_contract.md`
- `orchestration/docs/proposal_vs_accepted_event.md`
- `orchestration/docs/llm_provider_policy.md`
- `Promptbranch-as-Claude-Code-Shell-Operating-Model.updated-2026-05-03.txt`
- `promptbranch_claude_code_shell_mcp_operating_model.updated-2026-05-03.md`
- `promptbranch_mvp_plan_mcp_ollama_skills_agents_2026-05-03.md`
- `docs/promptbranch_ask_reply_protocol_design_and_mvp_plan.md`
- `promptbranch_native_release_lifecycle_todo.md`
- `docs/promptbranch_mvp_current_state_and_plan_2026-05-24.md`
- `docs/mvp-definition-of-done.md`
- `docs/release-v0.1.3.md`
- `docs/release-v0.1.4.md`
- `docs/release-v0.1.5.md`
- `docs/release-v0.1.6.md`
- `docs/release-v0.1.7.md`
- `docs/repair-v0.1.7.1.md`
- `docs/release-v0.1.8.md`
- `docs/release-v0.1.9.md`

## Editing the draw.io source

Open:

```text
docs/design/promptbranch-mvp-living-design.drawio
```

in diagrams.net/draw.io. Update only the region affected by the current release when possible. Keep the actual MVP identity box prominent so future readers do not confuse the generic Promptbranch shell work with the `json_orchestration_state_mvp` line.
