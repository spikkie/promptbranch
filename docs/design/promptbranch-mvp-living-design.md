# Promptbranch MVP Living Design

Release: `v0.1.66`  
Status: source-of-truth design note plus editable draw.io source and PB application design freshness guard  
Related diagram: `docs/design/promptbranch-mvp-living-design.drawio`
Related class diagram: `docs/design/promptbranch-class-diagram.drawio`

## 2026-08-06 PB MVP checkpoint

Accepted/current artifact evidence now establishes `v0.1.124` as the locally adopted artifact baseline while the installed Promptbranch runtime remains `v0.1.123.2.6`. The native candidate lifecycle reached `candidate_mvp_complete`. This proves the Promptbranch environment release workflow, not yet a separate application-development workflow.

The editable draw.io source adds a page named `PB MVP Status — v0.1.124`, which separates:

- proven Promptbranch control-plane and artifact-lifecycle capabilities;
- remaining PB-environment hardening;
- the not-yet-proven external application/tool lifecycle.

Detailed status and roadmap: `docs/design/promptbranch-pb-mvp-status-2026-08-06.md`.

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

- `docs/design/orchestration/docs/json_orchestration_state_mvp.md`
- `docs/design/orchestration/docs/json_orchestration_state_mvp_v0_1_0_high_level_canvas.md`
- `docs/design/orchestration/docs/json_orchestration_state_mvp_v0_1_0_low_level_canvas.md`

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

The actual MVP is now represented by the consolidated design/control tree under `docs/design`:

```text
docs/design/
  promptbranch-mvp-living-design.md
  promptbranch-mvp-living-design.drawio
  promptbranch-parallel-execution-architecture.md
  orchestration/
    README.md
    docs/
      current_status.md
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
      accepted_events/
      grills/
    state_machines/
```

The previous root-level `orchestration/` directory was a design/control surface, not runtime code. In v0.1.54 it is intentionally moved under `docs/design/orchestration/` so the project has one canonical design home.

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
- Release doctor/config/install/lifecycle/checkpoint/docs-status/baseline-status commands now have read-only planning/diagnostic surfaces.
- CI-style development flow is explicit: focused development can continue across monotonic dev candidates while full release-control is deferred until the adoption checkpoint.
- Living design validation exists through `pb release docs-status --json`.
- Post-adoption baseline alignment can be verified read-only through `pb release baseline-status --json`.
- `v0.1.58` is the accepted baseline for the PB application design documentation release and the base for the current `v0.1.59` docs-status freshness guard slice.
- Grill validation checks that committed G0-G6 examples recommend only k8s-game MVP state-machine transitions matching their stage.
- `v0.1.56` added the first read-only accepted-event fixture and validator for G0. `v0.1.57` extends that accepted-event fixture coverage to G1-G6 so every committed grill stage has a read-only accepted-event counterpart without mutating runtime workflow state.

- `v0.1.58` adds application-level PB design documentation and extends the existing editable draw.io sources with activity, data-flow, state-transition, role-component, and release-state pages. See `docs/design/promptbranch-application-design.md`, `docs/design/promptbranch-class-diagram.drawio`, `docs/design/promptbranch-mvp-living-design.drawio`, and `docs/diagrams/promptbranch-lifecycle/promptbranch_lifecycle_commands.drawio`.
- `v0.1.59` extends `pb release docs-status` so the PB application design document and all three editable diagram sources are checked as read-only release surfaces. Missing role/scope language, missing draw.io references, or missing required draw.io pages now block docs-status.

- `v0.1.60` adds `docs/design/promptbranch-release-baseline-evidence.md` and extends `pb release docs-status` with a `baseline_evidence` guard. The guard documents and validates that the locally accepted Promptbranch artifact is authoritative after adoption, even when a transient sandbox ZIP checksum differs from the accepted local artifact.
- `v0.1.61` adds `docs/design/promptbranch-living-design-overview.html` and `docs/design/promptbranch-living-design-overview.md` as repo-owned documentation for the editable living-design draw.io source and the whole PB authority model. It extends `pb release docs-status` with a `living_design_overview` guard and targeted tests that verify the HTML references `docs/design/promptbranch-mvp-living-design.drawio` and the PB control-plane / ChatGPT execution-surface split.
- Orchestration design/control surfaces are consolidated under `docs/design/orchestration/` as the canonical location.
- `pb release status-guide --json` now exposes a read-only operator runbook with required commands for the detected context.

### Current development-line reality

The accepted baseline and development head may differ:

```text
accepted baseline: last full-test/adopted artifact from pb artifact current
development head:  latest monotonic candidate installed/tested with focused checks
```

That is intentional during development. It becomes a release problem only if adoption is attempted without full release-control and source/adopt verification.


## PB application design documentation

`v0.1.58` added `docs/design/promptbranch-application-design.md` as the
application-level design note for the role split between `pb` and ChatGPT.
`v0.1.59` makes that design note release-checkable through docs-status. It
contains a Git-readable Mermaid activity diagram, data-flow diagram, and
state-transition diagram. The same release extends the editable draw.io sources
with visual pages for those diagrams and related role/release-state views:

```text
docs/design/promptbranch-application-design.md
docs/design/promptbranch-class-diagram.drawio
docs/design/promptbranch-mvp-living-design.drawio
docs/diagrams/promptbranch-lifecycle/promptbranch_lifecycle_commands.drawio
```

The core rule is unchanged:

```text
pb validates and gates operational state.
ChatGPT reasons, grills, and proposes.
Assistant prose is advisory until pb verifies schema, state, artifacts, and evidence.
```

The `v0.1.59` docs-status guard requires the PB application design surface to
remain linked, parseable, and semantically aligned with the authority boundary:

```text
Workspace = current ChatGPT Project
Task      = current chat/conversation inside that project
Artifact  = current repo/source bundle/release ZIP
backend-first reads
transactional writes
accepted baseline / artifact continuity
```

## What we are trying to achieve

The actual MVP should produce a safe, typed orchestration loop:

```text
intent
  -> ChatGPT grill proposal
  -> Promptbranch schema/policy validation
  -> read-only accepted/rejected JSON event fixture
  -> evidence collection
  -> release artifact candidate
  -> artifact intake verification
  -> guarded adoption
  -> next task from known state
```

The editable draw.io source now includes a second page named `Ask Reply JSON Data Flow`. It shows the concrete JSON objects passed through the ask/reply process:

```text
promptbranch.ask.request JSON
  -> ChatGPT task reply
  -> promptbranch.ask.reply JSON
  -> parsed reply record JSON
  -> artifact candidate JSON
  -> ZIP verification JSON
  -> candidate registry / artifact current JSON
  -> next ask from accepted baseline
```

The key rule is that JSON records are operational, while assistant prose, links, and claimed validation are advisory until Promptbranch validates the schema, baseline, artifact filename/version, ZIP hygiene, and release-control/adoption evidence.

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
| Grilling model | ChatGPT challenges intent/scope/evidence without becoming authority | G0-G6 model documented and checked against the k8s-game MVP state machine | add accepted-event fixtures after read-only transition validation stays stable |
| Shell model | Stable workspace/task/artifact grammar | mostly established | continue documenting canonical forms |
| MCP/local agent | Promptbranch-native host/client/server loop | read-only paths exist | harden host-smoke/run/skill flows |
| Skills | Reusable local operating procedures | read-only skill registry exists | keep local-only until validation is stronger |
| Ask/reply protocol | Machine-readable ChatGPT replies | design and partial implementation exist | prove real artifact roundtrip end-to-end |
| Artifact intake | Candidate download/verify/migrate/adopt | mature but needs repeated live proof | guarded adoption from verified candidate |
| Native release lifecycle | Move repo-local lifecycle into Promptbranch | read-only doctor/config/install/lifecycle planning exists | controlled install/source/test/adopt in separate slices |
| CI-style dev flow | Focused tests during dev, full test at checkpoint | explicit dev-status/checkpoint/baseline-status/status-guide commands exist | keep monotonic dev versions, no version rewrites |

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
- `docs/design/orchestration/docs/json_orchestration_state_mvp.md`
- `docs/design/orchestration/docs/json_orchestration_state_mvp_v0_1_0_high_level_canvas.md`
- `docs/design/orchestration/docs/json_orchestration_state_mvp_v0_1_0_low_level_canvas.md`
- `docs/design/orchestration/docs/global_mvp_plan.md`
- `docs/design/orchestration/docs/detailed_mvp_setup_plan.md`
- `docs/design/orchestration/docs/k8s_game_mvp_contract.md`
- `docs/design/orchestration/docs/proposal_vs_accepted_event.md`
- `docs/design/orchestration/docs/llm_provider_policy.md`
- `docs/design/promptbranch-mvp-gap-analysis.md`
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
- `docs/release-v0.1.10.md`
- `docs/release-v0.1.11.md`
- `docs/release-v0.1.13.md`
- `docs/release-v0.1.14.md`
- `docs/release-v0.1.15.md`
- `docs/release-v0.1.16.md`
- `docs/release-v0.1.17.md`
- `docs/release-v0.1.18.md`
- `docs/release-v0.1.18.1.md`
- `docs/release-v0.1.19.md`
- `docs/release-v0.1.20.md`
- `docs/release-v0.1.21.md`
- `docs/release-v0.1.22.md`
- `docs/release-v0.1.24.md`
- `docs/release-v0.1.25.md`
- `docs/release-v0.1.26.md`
- `docs/release-v0.1.27.md`
- `docs/release-v0.1.28.md`
- `docs/release-v0.1.29.md`
- `docs/release-v0.1.30.md`
- `docs/release-v0.1.32.md`
- `docs/release-v0.1.33.md`
- `docs/release-v0.1.35.md`
- `docs/release-v0.1.36.md`
- `docs/release-v0.1.37.md`
- `docs/release-v0.1.34.md`
- `docs/release-v0.1.31.md`
- `docs/release-v0.1.23.md`

## Editing the draw.io source

Open:

```text
docs/design/promptbranch-mvp-living-design.drawio
```

in diagrams.net/draw.io. Update only the region affected by the current release when possible. Keep the actual MVP identity box prominent so future readers do not confuse the generic Promptbranch shell work with the `json_orchestration_state_mvp` line.


## Release-status UX

`pb release status-guide --json` is the read-only command chooser for release-state inspection. It does not verify or mutate state; it tells the operator whether the current context should use the correct command, and it now includes a `recommended_sequence` runbook so operators can run the required read-only checks in order:

- `pb release baseline-status --json` after adoption, when runtime/source/artifact are expected to align.
- `pb release checkpoint --mode continue --json` for installed-but-not-adopted development candidates.
- `pb release dev-status --json` for inventory and baseline-versus-development-head inspection.
- `pb test smoke --json` as the required cheap runtime smoke after focused dev-candidate installs.

`v0.1.16` extended the guide with an explicit checkpoint threshold meter so the operator can see how many focused-development releases remain before a full-test/adoption checkpoint is recommended. `v0.1.17` adds a pre-threshold planning notice: when the current development candidate is one normal release away from the full-test/adoption threshold, `status-guide` reports the expected threshold version and adds a required operator-planning step to the read-only runbook.

`v0.1.18` turns that threshold notice into an actionable full-test/adoption preparation runbook when the threshold is reached. The guide remains read-only and does not execute tests or adoption, but it now includes the exact full release-control command and an explicit `adopt-current` command to run only after the full test is green. `v0.1.18.1` repairs cleanup idempotency in the full browser suite and becomes the accepted repair baseline after full release-control and adoption.

`v0.1.19` resets the release-status UX after that adoption checkpoint: the post-adoption status-guide runbook now shows the next normal release plan, including the expected next normal candidate artifact and the status/checkpoint commands to use after that candidate is built. This makes repair-baseline continuity explicit: the next normal release is built from the accepted repair baseline, not from the original normal release.

`v0.1.20` extends the development checkpoint handoff itself: when `pb release checkpoint --mode continue --json` reports that focused development may continue, it now includes explicit status-guide and checkpoint commands for the next monotonic development candidate after that candidate is built. This keeps the operator loop deterministic across focused development slices without implying adoption or full-test completion.

`v0.1.21` adds the same next-development handoff to `pb release status-guide --json` so the command chooser and checkpoint report the same after-build status-guide/checkpoint commands for the next monotonic development candidate. This matters when an operator captures only `status-guide` output before deciding whether to build the next candidate.

This keeps `baseline-status` post-adoption only while making the correct development-mode path discoverable and executable as an explicit read-only runbook.



### v0.1.22 — plain-text next-candidate handoff

`v0.1.22` adds the same next-development handoff to non-JSON `pb release status-guide` and `pb release checkpoint --mode continue` output. JSON automation already had these fields; the plain text path now also shows the next artifact and the after-build status-guide/checkpoint commands, reducing copy/paste risk during operator-driven focused development.


### v0.1.24 — pre-threshold full-test countdown visibility

`v0.1.24` adds a read-only full-test checkpoint countdown to release status-guide and checkpoint output. The countdown exposes when focused development is near the configured full release-control/adoption threshold, including plain-text fields covered by smoke. This gives operators earlier warning before the threshold is actually reached while preserving the focused-development/no-adoption workflow.

### v0.1.25 — projected threshold-version clarification

`v0.1.25` clarifies `expected_threshold_version` semantics in `pb release status-guide`. When the current candidate is near the full-test/adoption threshold but the next release does not reach it yet, `expected_threshold_version` now points to the projected threshold candidate instead of blindly echoing the next development candidate. For example, if the accepted baseline is `v0.1.18.1`, the current dev head is `v0.1.24`, and two normal versions remain, the projected threshold version is `v0.1.26`, while `v0.1.25` remains a normal focused-development candidate. The field is advisory/read-only; checkpoint decisions still come from `pb release checkpoint --mode continue`.



### v0.1.26 — ask/reply JSON data-flow diagram

`v0.1.26` adds an editable draw.io data-flow page named `Ask Reply JSON Data Flow` to `docs/design/promptbranch-mvp-living-design.drawio`. The diagram makes the JSON handoff explicit: `promptbranch.ask.request` is generated by `pb ask --protocol`, ChatGPT returns a `promptbranch.ask.reply` envelope, Promptbranch parses and validates it, artifact candidates become JSON records, ZIP verification emits deterministic evidence, and adoption updates `pb artifact current` only after full release-control is green. This keeps the ask/reply protocol aligned with the candidate-before-accepted-baseline model and avoids treating assistant prose as operational truth.


### v0.1.27 — baseline-status next-development handoff

`v0.1.27` starts from the adopted `v0.1.26` baseline after the threshold checkpoint. It keeps runtime behavior unchanged and improves the post-adoption handoff: `pb release baseline-status` now reports the next development artifact and the status-guide/checkpoint commands to run after that next candidate is built. This makes the baseline-status path complete for the normal post-adoption workflow: verify the accepted baseline, then continue from the verified baseline into the next monotonic candidate without relying on local assumptions.

### v0.1.23 — smoke-tested plain-text status-guide handoff

`v0.1.23` extends `pb test smoke --json` with a bounded non-JSON `pb release status-guide` substep. The smoke runner now validates required stdout markers for the plain-text operator handoff, including the next development artifact and after-build status-guide/checkpoint commands. This turns the v0.1.22 plain-text UX into recurring smoke evidence instead of relying on manual log inspection.


### v0.1.28 — read-only full-test evidence/status

`v0.1.28` adds a read-only full-test evidence/status surface for the post-adoption and focused-development lifecycle. `pb release evidence-status` inspects local release logs and structured post-release validation summaries without running tests or mutating state. `pb release baseline-status --json` now embeds the same evidence summary so an accepted baseline can distinguish three states: adopted and aligned, adopted with machine-verifiable full-test evidence, or adopted with only operator-reported/implicit evidence. This closes the process gap observed around `v0.1.26`, where adoption and later full-test evidence could both be true but not clearly represented by the status commands.


### v0.1.29 — structured full-test evidence summary

`v0.1.29` turns the full-test evidence path from log inference into a structured release-control artifact. When `chatgpt_claudecode_workflow_release_control.sh --run-tests` runs the full `pb test full` plus `pb test report` block, it now writes `post_release_validation.<version>.summary.json` under the versioned release log directory. `pb release evidence-status` already treats a green structured summary as high-confidence evidence, so future accepted baselines can be proven by machine-readable validation data instead of only release-log marker inference. The slice remains focused on evidence generation and reporting; it does not change adoption, Project Source upload, ZIP import semantics, or browser automation.

### v0.1.30 — baseline-status development checkpoint artifact selection

`v0.1.30` repairs a read-only operator-handoff defect in `pb release baseline-status`. When an installed development candidate is ahead of the accepted baseline and the operator accidentally runs `baseline-status --version <candidate>` without passing `--artifact`, the development checkpoint command now prefers the matching local candidate ZIP when it exists. This prevents the handoff from mixing the candidate version with the previously accepted artifact path. The slice is intentionally limited to read-only status guidance, tests, and documentation; it does not change adoption, Project Source upload, ZIP import, full-test execution, or browser automation.



### v0.1.31 — strict skip-source-add preservation

`v0.1.31` hardens the release-control source-add guard. A focused install run with `--skip-source-add` must not call `promptbranch src add`, even when the workflow delegates to the candidate ZIP's embedded `chatgpt_claudecode_workflow_release_control.sh`. The script now carries the skip intent through `PROMPTBRANCH_RELEASE_SKIP_SOURCE_ADD=1`, double-checks that guard before Project Source mutation, prints an explicit skip marker, and adds regression coverage for the Stage-0 delegated install path. This keeps local candidate install/checkpoint/smoke runs clearly separated from Project Source mutation and adoption.


### v0.1.32 — development-candidate next-normal guidance cleanup

`v0.1.32` cleans up read-only status-guide output for installed development candidates. When the runtime or selected artifact is already ahead of the accepted baseline, `next_normal_*` guidance from the accepted baseline is intentionally suppressed because it can point backward relative to the active development head. Development-candidate output now keeps the canonical path on `next_development_*` fields and records a `suppressed_next_normal_guidance` explanation, while post-adoption baseline output still exposes the normal next-release handoff. This keeps operator guidance aligned with the actual lifecycle context.

### v0.1.33 — checkpoint continue-mode warning contextualization

`v0.1.33` cleans up read-only checkpoint output for explicit focused-development candidates. When `pb release checkpoint --mode continue` is evaluating the currently installed development head and the complexity threshold still allows focused development, the install-plan warning `release_install_candidate_not_next_normal_version` is now contextualized instead of promoted as a top-level checkpoint warning. The nested install-plan evidence remains visible, and adoption mode still preserves the warning. This keeps continue-mode operator output focused on actionable risks while retaining strict full-test/adoption safety boundaries.

### v0.1.35 — focused development DoD and MVP-state guidance

`v0.1.35` adds a read-only focused-development definition-of-done payload to `release status-guide` and `release checkpoint`. The payload summarizes the accepted baseline, current development candidate, next development version, countdown state, focused-continue evidence, and the adoption checkpoint evidence required before a candidate may become accepted. It is advisory only and does not install, test, adopt, upload Project Sources, or mutate Git.

### v0.1.34 — full-test countdown planning window

`v0.1.34` makes the read-only full-test/adoption countdown enter its `near_threshold` planning state when the minimum remaining distance to the configured threshold is four focused releases. This keeps focused development allowed while making adoption planning visible earlier, before the projected threshold release. The change does not run tests, adopt artifacts, upload Project Sources, or mutate Git; it only improves operator guidance.


### v0.1.36 — pre-threshold planning notice alignment

`v0.1.36` aligns the read-only pre-threshold planning notice with the active full-test/adoption countdown. When the countdown is active but the configured threshold has not yet been reached, `release status-guide` now marks the planning notice and operator-plan step active while keeping `full_test_recommended_now=false` and leaving full release-control/adoption commands optional. This keeps adoption planning visible without prematurely forcing the expensive full-test checkpoint.


### v0.1.37 — threshold handoff and Promptbranch class diagram

`v0.1.37` is the threshold-handoff slice for the focused-development line that started after accepted baseline `v0.1.29`. It adds a compact read-only `threshold_handoff` payload to release status-guide and checkpoint output so the operator can distinguish ordinary focused continuation from the point where full release-control and adoption evidence must become the next gate. The handoff exposes the current candidate, expected threshold version, full-test command, adopt-current command, next safe operator step, and the class diagram source path. The release also adds `docs/design/promptbranch-class-diagram.drawio`, an editable diagrams.net class diagram covering the CLI, state store, artifact registry, release guidance/checkpoint classes, install plan, threshold handoff, release-control script, Project Source client, MCP host/server, and skill registry.


### v0.1.38 — profile-pool leases for parallel task reads

`v0.1.38` rebases the profile lease/pool solution onto the `chatgpt_claudecode_workflow-2` line. Browser-backed `pb task` commands can now lease cloned profile-pool slots through `--profile-pool`, allowing parallel task listing/show/answer inspection without opening the same physical Chromium/Patchright user-data-dir concurrently. The slice also adds `pb test release-live --json` as an explicit live browser gate around `visual-artifact-roundtrip`, while keeping `pb test full` deterministic. The operator state file remains rooted at the selected seed `--profile-dir`; the leased slot is used only for browser automation.


### v0.1.39 — read-only ChatGPT rate-limit diagnostics

`v0.1.39` adds `pb debug rate-limit --json` as a first-class diagnostic for the ChatGPT conversation-history guardrail. The command captures visible modal text, observed `/backend-api/*` `403`/`429` responses, `retry-after` when exposed, persisted cooldown state, and a safe pause policy. Guardrail detection is read-only and does not attempt bypass or direct mutation; service-level retry loops treat the rate-limit modal timeout as non-retryable so Promptbranch pauses instead of amplifying the restriction. The release also documents the current private `https://chatgpt.com/backend-api` surfaces Promptbranch reads or observes in `docs/chatgpt_backend_api_surfaces.md`.


### v0.1.41 — parallel execution architecture first slice

`v0.1.41` opens the Promptbranch parallel execution architecture line. The slice documents the resource-lock model in `docs/design/promptbranch-parallel-execution-architecture.md`, adds the `promptbranch_parallel.py` operation classification registry, exposes the plan through `pb debug parallel-plan --json`, and routes browser-client `_log` diagnostics to stderr so JSON stdout can become strict enough for future parallel runners. This slice does not add the scheduler or service-profile queue yet; it creates the executable metadata and test plan that later slices must build on.


## v0.1.62 documentation site scaffold

`v0.1.62` adds a Material-for-MkDocs-style source scaffold: `mkdocs.yml`, `docs/index.md`, `docs/design/index.md`, and `docs/releases/index.md`. The new `docs_site` guard in `pb release docs-status` verifies that these navigation surfaces reference the living-design HTML overview, PB application design, release baseline evidence, MVP living design, MVP gap analysis, orchestration current status, and recent release notes. Rendered `site/` output remains out of scope and must not be committed.


## v0.1.63 documentation site link-integrity guard

`v0.1.63` extends the `docs_site` guard so it validates repo-local link integrity for MkDocs navigation and documentation index links. This closes the gap where the documentation scaffold could exist but point to missing or renamed files. The slice remains documentation-only: no rendered `site/` output, runtime behavior, source mutation, browser automation, or artifact-adoption behavior changes are included.


## v0.1.64 documentation site build-readiness guard

`v0.1.64` adds `docs/site.md` as the operator-facing documentation-site policy page and extends the `docs_site` docs-status guard with `build_readiness`. The guard verifies that `mkdocs serve`, `mkdocs build`, the source-only policy, and the generated `site/` exclusion rule are documented. It does not require MkDocs to be installed and does not commit rendered output.


## v0.1.65 release lifecycle config guard

`v0.1.65` introduces the checked release lifecycle config contract. `.promptbranch-release.yml` is validated by `pb release config --json` for safe artifact naming, repo-relative paths, lifecycle hook templates, and read-only behavior. This is a prerequisite for later native lifecycle phases; it does not execute hooks or mutate release state.

## 2026-08-06 extended release roadmap

The editable diagram now also contains a page named `Release Roadmap — v0.1.125 to v0.1.134`. It preserves the existing `v0.1.125`, `v0.1.126`, and `v0.1.127` scopes, then shows the boundary between PB environment hardening and the first external application-development track.

The roadmap is authoritative only together with `docs/project/plan-state.json` and `docs/project/pb-mvp-roadmap-v0.1.124.md`.


## v0.1.125.2 repair gate

The draw.io source includes a dedicated repair page showing the accepted `v0.1.124` baseline, failed `v0.1.125` repeatability proof, failed `v0.1.125.1` full validation, active `v0.1.125.2` authority-fixture repair, and the explicit acceptance gate before `v0.1.126`. The repair remains inside the Promptbranch environment/control plane and does not start external application development.

## v0.1.125.3.2 canonical release-state-machine gate

The release lifecycle is now represented by one SHA-bound durable attempt with sequential states from `DECLARED` through `FINAL_VERIFIED`. Every reached state is independently re-evaluated; candidate registration is automatic; candidate tests run from exact bytes in a hermetic environment; acceptance/adoption require explicit authority; and interrupted runs resume at the next legal transition.
