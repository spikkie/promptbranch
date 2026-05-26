# Promptbranch MVP Definition of Done

Status: canonical MVP gate
Scope: `chatgpt_claudecode_workflow` / Promptbranch as a constrained Claude-Code-like workflow shell
Baseline introduced: `v0.0.273`

## Purpose

This document defines when the Promptbranch MVP is considered done.

The MVP is not finished merely because individual commands exist, individual ZIPs can be produced, or a release can be manually repaired. The MVP is finished when the complete operator loop can run repeatedly from the current accepted baseline through a structured ask, artifact intake, verification, guarded adoption, and continuation from the newly adopted baseline.

## MVP boundary

The MVP covers the minimum safe control-plane workflow around ChatGPT Projects:

- select a ChatGPT Project as the workspace
- select a chat/conversation as the task
- issue a protocol-aware ask
- parse a machine-readable assistant reply
- discover a candidate release artifact
- download the candidate only when explicitly requested
- verify the ZIP before migration or adoption
- migrate the verified ZIP as a candidate, not as an accepted baseline
- run guarded validation before adoption
- adopt only after green validation
- verify that current artifact/source/runtime state matches the accepted release
- continue the next ask from the accepted baseline

## Required operator workflow

The MVP is done when the following workflow succeeds end-to-end without manual repair:

```bash
pb ws use "Claude Code workflow in ChatGPT"
pb task use <task>

pb ask "Build next release from current baseline" \
  --protocol \
  --json

pb task answer parse --latest --json

pb artifact intake \
  --from-last-answer \
  --download \
  --verify \
  --migrate \
  --json

scripts/finalize-artifact-intake-mvp.sh \
  --version <candidate_version> \
  --target-version <next_version> \
  --require-real-candidate-mvp

pb artifact current --json

pb ask "Continue next slice" \
  --protocol \
  --from-current-baseline \
  --json
```

The same workflow must pass for at least two consecutive normal releases from clean accepted baselines.

For strict final Artifact Intake MVP validation from `v0.0.276.5`, `scripts/finalize-artifact-intake-mvp.sh --require-real-candidate-mvp` must run an artifact-producing `pb ask-release` for the target version and must prove `pb artifact intake --download --verify` with `download_performed=true` and `verification_performed=true`. A no-artifact protocol smoke is not sufficient for strict real-candidate proof.

Manual validation details for the finalizer are documented in `docs/howto/15-finalize-artifact-intake-mvp.md`. That manual is the operator reference for preflight checks, wrapper-contract tests, delegated post-release phases, evidence files, and failure triage.

## Required invariants

The MVP is done only when all of these invariants hold.

### State model

- Workspace, task, and artifact state are tracked separately.
- Switching a task must not mutate workspace state.
- Switching a workspace must not silently reuse an incompatible task.
- Artifact current state must represent an accepted baseline, not merely a downloaded or migrated candidate.

### Backend-first and transactional behavior

- Read paths prefer backend/network payloads where available, then saved Promptbranch state, then DOM fallback.
- Mutating paths are transactional: trigger, wait for settled/backend-confirmed state, re-read, verify, then update local state.
- No source add/remove/sync path may update Promptbranch state before persistence is verified.
- No refresh may race an in-flight save/commit path.

### Ask/reply protocol

- Protocol-aware asks include a request envelope.
- Automation uses the validated reply envelope, not assistant prose.
- Missing, malformed, ambiguous, or mismatched reply envelopes fail closed.
- Request ID and correlation ID mismatches fail closed.

### Artifact intake

- Candidate artifacts are extracted from the reply envelope first, with link/text fallback only when deterministic selection is possible.
- Artifact download requires an explicit operator flag.
- Downloaded artifacts are stored in the artifact inbox/quarantine before migration.
- A migrated artifact is a candidate release, not an accepted baseline.

### ZIP verification

A candidate ZIP must be rejected unless all required checks pass:

- ZIP opens successfully
- `VERSION` exists
- `VERSION` matches the candidate version
- filename matches the project artifact naming convention
- ZIP opens directly to repository contents, with no wrapper directory
- no `.pb_profile/`
- no `__pycache__/`
- no `.pytest_cache/`
- no `*.pyc` or `*.pyo`
- no log files
- no nested release ZIPs
- no local secrets or machine-specific state
- baseline continuity is valid
- repair-version rules are respected

### Validation and adoption

- Candidate adoption requires a green validation report.
- Adoption must verify `pb artifact current` after completion.
- Adopted artifact/source/runtime versions must match the candidate version or produce a clear classified failure.
- Post-release validation must write machine-readable summary artifacts.
- Post-release validation must print a human summary suitable for operator inspection.

### Continuation

- The next protocol ask must be able to read the accepted baseline automatically.
- The next ask must not continue from a stale local artifact, stale project source, or remembered version when current baseline state exists.

## Required failure behavior

The MVP is done only when these negative cases fail closed with clear status codes or categories:

- no reply envelope
- invalid reply JSON
- multiple reply envelopes
- request/correlation mismatch
- wrong project artifact name
- wrong candidate version
- stale baseline
- wrapper-folder ZIP
- ZIP hygiene failure
- candidate migration attempted before verification
- adoption attempted before green validation
- current artifact/source mismatch after adoption
- source mutation not verified
- UI or backend state changed unexpectedly during a mutation

## Required evidence artifacts

Each completed MVP release cycle must leave enough evidence for diagnosis:

- ask request JSON
- raw assistant answer or answer reference
- parsed reply JSON
- candidate intake record
- ZIP verification record
- candidate registry/current state
- post-release validation summary JSON
- lifecycle-status snapshot JSON
- lifecycle consistency/guard reports where enabled
- human final summary in terminal output

## Out of scope for MVP

These are useful, but they are not required for MVP completion:

- broad shell command execution
- autonomous repository editing
- autonomous source overwrite without explicit operator intent
- remote skill downloads
- write-capable MCP execution from model proposals
- Cursor or Claude Desktop as required MCP hosts
- full Promptbranch-native replacement of every repo-local release script
- Streamable HTTP MCP transport
- fully autonomous multi-release planning

## Post-MVP direction

After the MVP gate is satisfied, the next major direction is a native release lifecycle engine:

```text
pb release lifecycle --artifact <zip> --version <version> --json
```

That command should consolidate install, source add, project hooks, adoption, policy sync, Git safety, and final lifecycle reporting. Until then, repo-local finalizer/release-control scripts remain valid bridge tooling.

## Final MVP verdict rule

The MVP is done when the complete structured ask-to-adopt-to-next-ask loop works twice in a row from accepted baselines, with no manual ZIP repair, no stale baseline selection, no unverified mutation, and no unexplained operator intervention.
