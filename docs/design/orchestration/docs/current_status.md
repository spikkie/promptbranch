# JSON Orchestration State MVP — Current Status after v0.1.79

Updated for release: v0.1.79

## Purpose

This document reconciles the original `v0.1.x` orchestration objective with the actual accepted release line through accepted `v0.1.65` and the v0.1.66 release doctor candidate ZIP precheck slice.

The project remains on the same strategic goal:

```text
ChatGPT proposes structured JSON.
Promptbranch validates schema, policy, and state.
Only accepted events become trusted workflow state.
Artifacts still go through Final Artifact Intake.
```

## Current state

```text
latest accepted baseline:          v0.1.78.2.20.8.8
current development release:       v0.1.79
orchestration goal:                still active
execution authority:               Promptbranch only
critical-path provider:            ChatGPT only
local/Ollama provider:             rejected until new ADR + tests
```

## What has been completed

```text
v0.1.0  Opened the JSON Orchestration State MVP line.
v0.1.1  Continued orchestration foundation and validation work.
v0.1.20-v0.1.37  Hardened release-control, task/message, source/artifact, and validation surfaces needed by the shell workflow.
v0.1.38  Added browser profile lease/pool support so live tests do not collide on the same profile.
v0.1.39  Added read-only rate-limit diagnostics and backend API surface documentation.
v0.1.40  Reconciled these detours and added the read-only grill schema foundation.
v0.1.41-v0.1.53  Hardened backend diagnostics, source mutation locks, VERSION-driven service metadata, and release adoption verification.
v0.1.54  Consolidated the orchestration design/control surfaces under docs/design/orchestration and refreshed the living MVP design references.
v0.1.54.1  Repaired Project Source file persistence verification so file-source matches must be filename-anchored.
v0.1.55  Connects read-only grill validation to the k8s-game MVP state-machine transition rules.
v0.1.55.1  Repairs grill validator CLI path-label handling without advancing MVP scope.
v0.1.56  Adds the first read-only accepted-event fixture and validator that consumes a valid G0 grill recommendation without mutating runtime state.
v0.1.57  Extends accepted-event fixture coverage to G1-G6 so every committed grill stage has a read-only accepted-event counterpart.
v0.1.58  Adds PB application design documentation plus activity, data-flow, state-transition, role-component, and release-state draw.io pages.
v0.1.59  Makes the PB application design surface release-checkable through docs-status and blocks missing role/scope language or missing draw.io pages.
v0.1.60  Adds accepted-baseline evidence documentation and docs-status guard coverage for candidate/installed/adopted artifact semantics.
v0.1.61  Integrates living-design HTML overview into repo documentation and adds release-checkable HTML/draw.io/PB-authority-model validation.
v0.1.62  Adds a Material-for-MkDocs source scaffold and docs_site guard so PB design/release documentation is navigable from one entrypoint without committing rendered site output.
v0.1.63  Extends docs_site with repo-local link-integrity validation for MkDocs navigation and documentation index links.
v0.1.64  Extends docs_site with build-readiness validation for docs/site.md, preview/build commands, and generated site output exclusion.
v0.1.65  Adds a read-only release lifecycle config contract guard for .promptbranch-release.yml and pb release config --json.
v0.1.66  Makes pb release doctor consume .promptbranch-release.yml for read-only candidate ZIP prechecks, filename/config matching, VERSION consistency, ZIP hygiene, and accepted-baseline continuity.
v0.1.67-v0.1.78.2.20.8.8  Hardened project control surface, artifact adoption/current consistency, Project Source transaction diagnostics, live retained-project tests, and immutable Project deletion freeze.
v0.1.79  Resumes the normal JSON orchestration MVP line with a proposal-only event-intake schema, read-only validator, CLI command, and fail-closed tests.
```

## Drift assessment

The releases after the original `v0.1.0` plan are not goal drift by themselves. They are operational hardening needed to make the control plane safer.

The remaining risk is not conceptual drift, but authority drift:

```text
A ChatGPT grill envelope can recommend a next state.
Promptbranch must verify that the recommendation is allowed by the state machine.
The recommendation must remain proposal-only until a later accepted-event path records it.
```

v0.1.55 reduced that risk by validating each committed G0-G6 grill fixture against the canonical k8s-game MVP state machine. Invalid transitions, stage/transition mismatches, and project/state-machine mismatches now fail the read-only grill validator.

v0.1.56 added the accepted-event validation boundary: a committed accepted-event fixture must reference a valid grill fixture, preserve the source grill SHA-256, match the source recommendation, and match the canonical k8s-game MVP state machine. v0.1.57 expands that proof from G0 to all committed G0-G6 grill stages. The fixtures remain data-only and cannot record live workflow state.

## Active safety boundary

The grill layer is still proposal-only:

```text
- no source mutation
- no artifact adoption
- no Kubernetes deployment
- no local/Ollama critical-path provider
- no model execution authority
```

Promptbranch may validate grill envelopes and accepted-event fixtures. In v0.1.66 accepted events remain committed read-only fixtures only; they do not update Promptbranch runtime state or artifact/source registries. The PB application and baseline evidence, living-design overview, docs-site docs-status guards, release config guard, and release doctor candidate precheck are validation only and do not widen execution authority.

## Next planned orchestration work

After this release is accepted, the next narrow slice should remain read-only and may be selected from the consolidated living design:

```text
- add rejected-event fixtures that prove invalid grill recommendations remain non-authoritative
- extend docs-status so it checks accepted-event fixture coverage and source-grill hash freshness
- add accepted-event coverage checks for required stage completeness in a dedicated status command
```

Do not start game implementation or write-capable orchestration until the design/control surfaces remain stable after the state-machine transition validation slice.


## v0.1.65 release-control status

`v0.1.65` remains a read-only config-contract release. It does not widen orchestration authority, execution authority, source mutation, artifact adoption, browser automation, hook execution, Git mutation, or release lifecycle behavior.


## v0.1.66 release doctor candidate precheck rule

Release doctor now consumes `.promptbranch-release.yml` when an explicit candidate ZIP is provided. The command remains read-only and reports candidate evidence only; it must not install, upload Project Sources, execute hooks, adopt artifacts, update state, commit, or push.
