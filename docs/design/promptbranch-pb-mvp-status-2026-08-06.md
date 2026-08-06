# Promptbranch MVP status — 2026-08-06

## Executive position

Promptbranch is still the product under development and validation.

The current tests prove the Promptbranch environment and its workflows:

- CLI command routing and state scopes;
- ChatGPT Project, conversation, and Project Source integration;
- structured ask/reply contracts;
- release ZIP materialization and verification;
- candidate registry and lifecycle transitions;
- focused and full release validation;
- explicit local artifact acceptance and current-state proof.

They do **not** yet prove that Promptbranch can take a separate application or tool from product intent through architecture, controlled code changes, application tests, release, acceptance, and deployment.

The correct checkpoint is therefore:

```text
PB environment/control-plane release lifecycle: proven for the v0.1.124 path
PB application-development lifecycle: not yet proven end to end
```

## Current authoritative release roles

```text
Accepted/current PB artifact baseline: v0.1.124
Installed PB runtime code:             v0.1.123.2.6
Candidate lifecycle result:            candidate_mvp_complete
Project Source publication:            not performed for v0.1.124
Full candidate evidence:               direct transport passed
Optional exhaustive matrices:          not all demonstrated
```

The artifact/runtime difference is intentional in the current model: an accepted external release artifact may be current while the installed control-plane runtime has a different version. This distinction must remain visible and must never be reported as runtime alignment.

## What “MVP complete” means at different layers

### MVP-0 — control-plane and release foundation

Status: **substantially complete and operationally proven**.

Implemented capabilities include:

1. Explicit Workspace, Task, Source, and Artifact scopes.
2. Backend-first reads and transactional browser/UI writes.
3. Fail-closed source processing and persistence verification.
4. Structured Promptbranch ask/reply JSON envelopes.
5. Real downloadable ZIP artifact materialization.
6. ZIP verification for SHA-256, size, VERSION, layout, hygiene, and unsafe paths.
7. Candidate migration and registry state.
8. Candidate smoke/full testing and evidence records.
9. Explicit candidate acceptance and current-baseline verification.
10. PBAI application-architecture declaration, registry, executable, and operational validation surfaces.
11. Read-only MCP tools, skills, evidence collection, and bounded architecture-proof execution.
12. Impact-based development testing while preserving the strict release gate.

The v0.1.124 candidate path proved the native release candidate lifecycle through:

```text
structured request
→ real rendered ZIP
→ exact reply correlation
→ materialized/reused inbox artifact
→ ZIP verification
→ candidate migration
→ focused live source proof
→ full direct candidate test
→ explicit accept-candidate
→ artifact current verification
→ candidate_mvp_complete
```

### Artifact Intake / Candidate Lifecycle MVP

Status: **complete for the locally adopted artifact path**.

The lifecycle now correctly distinguishes:

- generated/untrusted reply output;
- downloaded or reused materialized ZIP;
- verified candidate;
- migrated candidate;
- tested candidate;
- adoption-eligible candidate;
- accepted/current artifact.

It also correctly blocks acceptance after failed or timed-out tests.

This completion does not mean every optional test transport, Project Source publication path, or general application workflow has been completed.

### MVP-1 — loop-based problem-solving engine

Status: **partially implemented**.

The loop has progressed through safe presentation and evidence layers:

- state-only walkthrough;
- planned-action walkthrough;
- controlled read-only execution/evidence surfaces;
- architecture and authority validation;
- execution-envelope and rollback concepts in the release gate.

The central missing capability is controlled application actuation. Promptbranch does not yet have end-to-end proof that it can:

1. select an external application target;
2. derive one bounded implementation slice;
3. authorize exact code/file changes;
4. execute those changes under a rollback-capable envelope;
5. run the application’s tests;
6. diagnose failures;
7. apply the smallest correction;
8. build and verify the application candidate;
9. accept or deploy it under explicit operator authority.

## What the recent v0.1.124 proof established

### Proven

- The assistant produced a real downloadable ZIP and a valid protocol reply.
- Promptbranch correlated the request, message, answer, candidate, and artifact identity.
- Legacy ZIP-kind normalization and exact inbox artifact reuse worked.
- ZIP verification and candidate migration worked.
- `project_source_add_text` accepted ChatGPT’s canonical `pasted.txt` backend identity while retaining exact logical and processing-stream correlation.
- The focused six-step source proof passed.
- The full direct candidate test passed with a sufficiently large timeout.
- The explicit candidate-test gate passed.
- Local artifact/state acceptance completed.
- `pb artifact current --json` matched the accepted candidate.
- `pb artifact candidate-run --json` reported `candidate_mvp_complete`.

### Not proven by that path

- A localhost transport run for the same final candidate.
- External-live and run-all test matrices.
- The complete strict source-kind matrix.
- A forced-fresh multi-transport evidence run.
- The sandbox mutation rollback gate in that final direct profile.
- Upload and exact verification of v0.1.124 as a ChatGPT Project Source.
- Installation of v0.1.124 as the PB runtime.
- Development of a separate application through PB.

## Known PB-environment hardening items

These are environment defects or policy decisions, not application features:

1. **Profile-sensitive test timeout**
   - The full profile exceeded the original 540-second wrapper timeout.
   - Full candidate testing succeeded with a 3600-second timeout.
   - The default should be derived from the selected profile or delegated release workflow.

2. **Pending candidate ZIP preservation/recovery**
   - A clean install removed the repo-root candidate ZIP while preserving its registry entry.
   - Candidate-test should restore the exact verified inbox artifact automatically, or release installation should preserve registered pending candidates.

3. **Final-summary consistency**
   - Earlier candidate-run outputs contained stale top-level inventory fields even when authoritative cycle and completion sections were correct.
   - Final summaries should be recomputed after lifecycle execution.

4. **Mandatory test-policy definition**
   - “Full” currently passed in direct mode, while additional transport and external-live variants remained optional or skipped.
   - The MVP must explicitly define which evidence is mandatory for environment release acceptance and which belongs to extended confidence testing.

5. **Project Source publication policy**
   - v0.1.124 was accepted as a local artifact/state baseline without Project Source mutation.
   - Decide whether PB Environment MVP completion requires the accepted release to be visible and verified as a ChatGPT Project Source.

## Recommended roadmap

### Phase A — freeze the PB Environment MVP contract

Goal: make the environment’s completion criteria unambiguous and repeatable.

Required outcomes:

- define mandatory and optional release-test profiles;
- fix full-profile timeout selection;
- preserve or automatically recover pending candidate ZIPs;
- remove stale summary/reporting contradictions;
- decide the Project Source publication requirement;
- record a single command sequence that proves the environment MVP without manual interpretation.

Exit criterion:

```text
A fresh environment can run one documented workflow that ends in an accepted/current PB artifact with every mandatory evidence group green and no manual state repair.
```

### Phase B — first external application pilot

Goal: prove that PB can develop something other than PB.

The pilot should:

- live in a separate repository;
- be small enough for one vertical slice;
- have deterministic tests and a visible output;
- declare its architecture and authority boundaries;
- avoid production deployment in the first run;
- use explicit human authorization for mutation and acceptance.

The current documentation identifies the Kubernetes game as the first future acceptance scenario. It should become an external pilot only after the PB environment contract is frozen; it must not be mixed into PB’s own runtime validation.

Exit criterion:

```text
PB drives one separate application from target and architecture through a controlled change, application tests, verified candidate artifact, and explicit acceptance.
```

### Phase C — controlled correction execution

Goal: turn the read-only/planned loop into bounded actuation.

Required capabilities:

- exact file/tool allowlists;
- pre-change snapshot and rollback proof;
- execution-envelope validation;
- test selection and result classification;
- smallest-correction planning;
- bounded retry count;
- fail-closed stop conditions;
- no Project Source, artifact, Git, or deployment mutation without explicit authority.

### Phase D — reusable application workflow

Goal: generalize the proven pilot.

Likely work:

- application templates and migrations;
- domain-module integration;
- multi-repository dependency and release-set planning;
- reusable test profiles;
- application artifact publication;
- explicit deployment adapters and post-deployment verification.

## Architecture interpretation

The architecture must always show two separate systems:

```text
System A: Promptbranch control plane
  The environment being developed and validated now.

System B: External application/tool
  The product that PB will eventually plan, change, test, release, and deploy.
```

Passing System A’s tests does not imply System B exists or works. The next major milestone is the controlled bridge from System A to the first real System B pilot.

## Updated editable diagrams

The following draw.io files now contain new status pages:

- `docs/design/promptbranch-mvp-living-design.drawio`
  - page: `PB MVP Status — v0.1.124`
- `docs/design/promptbranch-class-diagram.drawio`
  - page: `PB MVP Component Boundaries — Proven vs Planned`
- `docs/diagrams/promptbranch-lifecycle/promptbranch_lifecycle_commands.drawio`
  - page: `PB MVP Proven Lifecycle and Next Application Loop`

The new pages preserve the earlier design history while making the control-plane/application boundary and the next roadmap explicit.
