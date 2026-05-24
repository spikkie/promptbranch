# Promptbranch MVP — Current State and Step-by-Step Plan

Updated: 2026-05-24

## Scope and baseline note

This document reconciles the existing Promptbranch design documents with the implementation/release state visible in the current project context.

Important baseline distinction:

- Last explicitly proven accepted baseline in the visible conversation before this documentation release: `chatgpt_claudecode_workflow_v0.0.264.1.zip`.
- Latest accepted implementation artifact available for this release: `chatgpt_claudecode_workflow_v0.0.264.1.zip`.
- Before any new release work, run `pb artifact current --json` locally and continue from the latest accepted baseline reported there.

## Executive state

The MVP has moved from “planned Claude-Code-like workflow shell” to a partially proven control plane with two mature tracks:

1. **Ask/Reply + Artifact Intake** is now functionally proven through a real candidate lifecycle.
2. **Local Promptbranch-native MCP/agent/skills** is read-only, policy-gated, and now has release-readiness checks.

The remaining MVP gap is no longer basic protocol parsing or simple candidate migration. The remaining gap is **operator-grade lifecycle orchestration**: stable baseline reconciliation, finalizer/reporting consistency, browser mutation resilience, and a native release lifecycle command that reduces dependency on repo-local scripts.

## Current MVP tracks

### Track A — Workspace / Task / Artifact shell model

Status: **usable but still uneven**.

Implemented/available:

- Workspace/task/artifact are the correct core scopes.
- State can track current project, conversation, and artifact/source baseline independently.
- `pb task messages list`, `pb task answer parse`, explicit message/answer selectors, and global answer-id resolution now address the multi-answer reality of ChatGPT tasks.

Still weak:

- The command grammar exists, but older aliases and lower-level commands still leak into daily use.
- The task/message/answer UX improved, but should become the standard way to select protocol replies.

Next intent:

- Make message/answer identity first-class in all protocol and artifact-intake outputs.
- Prefer explicit selector commands over `--latest` whenever automation depends on a specific answer.

### Track B — Ask/Reply protocol and artifact intake

Status: **functionally proven MVP**.

Implemented/proven:

- Structured protocol request and reply envelope.
- Reply parsing with request/correlation validation.
- Artifact candidate extraction.
- Manual local-file artifact handoff for ChatGPT `sandbox:` artifacts.
- ZIP verification and hygiene checks.
- Migration to repo-root candidate release.
- Candidate-run lifecycle through test/adopt.
- Strict real-candidate MVP validation.
- Repair for the no-artifact smoke overwriting/latest-reply problem.
- Explicit answer selection support in artifact intake.

Remaining weak points:

- Browser-context automatic artifact download is still not solved; manual handoff remains required for `sandbox:` artifacts.
- `--latest` is unsafe after diagnostic chatter; explicit message/answer selectors are required for reliable automation.
- Finalizer and candidate-run logic must continue avoiding accidental coupling to the latest protocol smoke answer.

Updated design status:

- The original Ask/Reply MVP-F0..F7 should be marked as implemented/proven through the real-candidate MVP gate.
- Add a new MVP-F8: browser/manual artifact transport hardening.
- Add a new MVP-F9: protocol transcript identity and replay UX.

### Track C — Native release lifecycle

Status: **partially native, still not complete**.

Implemented/available:

- `pb release doctor` and release diagnostics.
- Release install planning and controlled install slices.
- Acceptance hook runner.
- Adopt + verify mechanics.
- Policy/Git sync safety work.
- `pb release lifecycle` exists as an orchestration surface in the recent line.
- Final Artifact Intake MVP validation can gate releases.

Still weak:

- The workflow is still partly split between Promptbranch-native commands and `scripts/finalize-artifact-intake-mvp.sh` / repo-local release-control scripts.
- Browser full-suite failures can still block validation even when the release code path itself is not the failing surface.
- The finalizer should better distinguish product failure from external browser/session environment failure.

Next intent:

- Consolidate finalizer + lifecycle into one native command sequence.
- Make post-adoption proof and protocol-smoke proof independent and explicitly named.
- Improve environment classification for browser service failures.

### Track D — Local MCP host/client and deterministic agent

Status: **read-only MVP is solid and should remain read-only by default**.

Implemented/available:

- `pb mcp serve --path .`
- MCP stdio host/client smoke.
- `pb agent run` as canonical host/client run path.
- Read-only tools: state, workspace, task, filesystem read/list, git status/diff summary, artifact registry/current/verify.
- `pb agent mcp-call`, `pb agent tool-call`, `pb agent host-smoke`.
- Ollama proposal/summarization paths exist but remain non-authoritative.

Still weak:

- Local LLM planning remains untrusted.
- Write/process tools should stay blocked unless a deterministic policy gate and transactional verification exist.

Next intent:

- Keep expanding deterministic read-only skills before write-capable agent behavior.
- Treat Ollama as summarizer/proposer only.

### Track E — Skills and release-readiness

Status: **beyond initial repo-inspection MVP**.

Implemented/available:

- Built-in `repo-inspection` skill.
- Built-in `release-readiness` skill.
- `pb skill list/show/validate`.
- `pb agent run --skill repo-inspection ...`.
- `pb agent run --skill release-readiness ...`.
- `pb agent release-readiness --json`.
- `pb agent release-readiness --require-ready --json`.

Remaining weak:

- Release-readiness is read-only and should not be confused with final acceptance.
- Skill outputs need stable JSON schemas if they are to become CI/finalizer inputs.

Next intent:

- Promote release-readiness from useful report to formal preflight gate with documented blockers/warnings.
- Add tests that prove it never mutates source/artifact/Git state.

### Track F — Browser/project-source reliability

Status: **improved but still highest operational risk**.

Implemented/available:

- Source save persistence checks improved after the early-refresh-aborting-save failure.
- Persistent browser-context startup retry/classification repair exists in the latest inspected artifact line.
- Recoverable browser startup errors can be classified as service unavailable rather than generic failure.

Still weak:

- Browser automation remains the biggest non-deterministic dependency.
- A browser/session failure can still appear during final validation even when the release scope itself is unrelated.

Next intent:

- Separate environment availability from product correctness in finalizer summaries.
- Add retry/backoff and explicit browser-context health diagnostics before running expensive full browser suite.

## Design documents that need updating

### 1. `docs/promptbranch_ask_reply_protocol_design_and_mvp_plan.md`

Update required:

- Mark MVP-F0..F7 as implemented/proven rather than planned.
- Add explicit note that real candidate lifecycle was proven through manual local-file handoff and strict real-candidate gate.
- Add MVP-F8: artifact transport hardening.
- Add MVP-F9: protocol transcript identity/replay.
- Update artifact intake examples to prefer explicit selectors:

```bash
pb artifact intake \
  --from-last-answer \
  --message-id <user-message-id-or-index> \
  --answer-id <assistant-answer-id-or-prefix> \
  --local-file ~/Downloads/chatgpt_claudecode_workflow_vX.Y.Z.zip \
  --verify \
  --migrate \
  --json
```

### 2. `promptbranch_claude_code_shell_mcp_operating_model.md`

Update required:

- Replace the old “implemented through v0.0.143” status with the current v0.0.260+ line.
- Add release-readiness as a built-in read-only skill/gate.
- Clarify that Ask/Reply + Artifact Intake is now part of the operating model, not merely future release infrastructure.
- Preserve the core principle: Promptbranch is the local control plane; ChatGPT.com is the execution surface.

### 3. `promptbranch_mvp_plan_mcp_ollama_skills_agents_2026-05-03.md`

Update required:

- Mark Phase 1 and Phase 2 largely done.
- Add release-readiness skill and gate to Phase 2/2b.
- Keep Ollama in proposal/summarization only.
- Do not move source/artifact writes into agent control yet.

### 4. `promptbranch_native_release_lifecycle_todo.md`

Update required:

- Mark doctor, install, acceptance hook, adopt/verify, policy/Git sync, lifecycle and strict finalizer as partially implemented.
- Add a new remaining section: “lifecycle consolidation and environment-failure classification.”
- Add requirement that finalizer reports whether a failure is product-code, artifact-state, browser-environment, network/rate-limit, or operator-precondition.

## Step-by-step plan from here

### Step 1 — Establish the true accepted baseline

Run locally:

```bash
pb artifact current --json | python3 -m json.tool
pbv
```

Decision:

- If current is `v0.0.264.1`, continue normal development from `v0.0.264.1`.
- If current is later, continue from the latest accepted repair/normal version reported by `pb artifact current`.
- Do not build from any uploaded ZIP just because it exists.

Acceptance:

- Runtime version, artifact current, source current, and registry current are understood.

### Step 2 — Update the design docs as a documentation-only release

Target next normal release from the accepted baseline.

Scope:

- Update the four design docs listed above.
- Add one current-state summary doc under `docs/`, using this document as source.
- No behavior changes.
- No protocol changes.
- No browser automation changes.

Acceptance:

- Docs are internally consistent with the real-candidate MVP proof.
- Release notes clearly state this is documentation-only.
- Full finalizer passes.

### Step 3 — Harden finalizer classification

Scope:

- Make finalizer distinguish:
  - product validation failure
  - artifact state/baseline failure
  - browser environment/session failure
  - service/network/rate-limit failure
  - operator precondition failure
- Preserve nonzero exit for strict failures, but include structured failure class.

Acceptance:

- Browser-context startup failure returns a classified environment/service failure.
- Product-code success is not hidden by ambiguous HTTP 500 wording.

### Step 4 — Make release-readiness a pre-finalizer gate

Scope:

- Run `pb agent release-readiness --require-ready --json` before expensive browser/full validation.
- Include the release-readiness report in release logs.
- Do not let release-readiness adopt or mutate anything.

Acceptance:

- Dirty Git, version mismatch, missing artifact current, or baseline mismatch fail early with readable blockers.
- Clean state passes without mutation.

### Step 5 — Consolidate Artifact Intake MVP status into `pb release lifecycle`

Scope:

- Expose the full proven path through a native lifecycle command:
  - protocol proof
  - candidate proof
  - test/adopt proof
  - post-adoption current proof
  - protocol smoke proof
- Keep repo-local scripts as compatibility wrappers.

Acceptance:

- One command can report the full state without relying on manually reading separate logs.

### Step 6 — Improve artifact transport

Scope:

- Keep manual `--local-file` supported.
- Add better detection/reporting for `sandbox:` / browser-context-only artifacts.
- Optionally add browser-assisted artifact download only after environment diagnostics are stable.

Acceptance:

- `sandbox:` candidates fail with a precise `manual_download_required` or equivalent status.
- Manual import records selected request/message/answer identity.

### Step 7 — Stabilize skills and read-only local agent schemas

Scope:

- Freeze JSON schemas for:
  - repo-inspection report
  - release-readiness report
  - skill validation result
  - agent run result
- Keep all skill/agent behavior read-only.

Acceptance:

- Reports can be consumed in CI/finalizer tests.
- Write tools remain blocked by default.

### Step 8 — Only then consider controlled write tools

Scope:

- Controlled test execution first.
- Artifact verify/package second.
- Source sync last.

Acceptance:

- Every write has precheck, before/after snapshot, collateral-change detection, and verified state update.

## Immediate next development recommendation

Build the next release as **documentation + release-readiness/finalizer clarity**, not a new mutation feature.

Recommended next slice:

```text
next normal release:
- update design docs to current state
- add docs/current-mvp-state-and-plan.md
- add release-readiness pre-finalizer report wiring if not already present
- improve finalizer failure classification wording only
- no new write-capable agent tools
```

## Critical assessment

Strengths:

- The core protocol/artifact-intake path is no longer theoretical.
- Real candidate import, verification, migration, test/adopt, and current proof have been exercised.
- The local MCP/agent/skills track is correctly constrained to read-only operations.

Weaknesses:

- Browser automation remains the main operational risk.
- Design docs lag behind the release line.
- Lifecycle orchestration is still split across native commands and scripts.

Unknowns:

- Whether future uploaded artifacts after `v0.0.264.1` have been accepted on the operator machine.
- Whether the latest browser-context repair eliminates the finalizer failure class in repeated runs.
- Whether release-readiness should become mandatory for all finalizers or only strict MVP finalizers.

Next step:

- Confirm local current baseline.
- Create a documentation-only release updating the design docs to this state.
