# v0.1.126.1.1 — canonical fingerprint and blocked-ETA semantics repair

## Authority

- Built from the exact immutable `v0.1.126.1` release artifact.
- Accepted/current baseline remains `v0.1.125.3.4.2` until this repair reaches `FINAL_VERIFIED`.
- Release mode: repair; no scope advance.

## Live failure repaired

The first live `v0.1.126.1` attempt reached `CANDIDATE_REGISTERED` and then failed deterministically at `RUNTIME_PREPARED / candidate_image_built`. The state machine passed a full-source fingerprint into the Docker build, while the Dockerfile independently recomputed a different three-file version fingerprint. The exact candidate therefore failed before the image could be created.

This repair introduces one canonical implementation, `promptbranch_source_fingerprint.py`, used by the release state machine and Docker build-context verification. The identity binds relative path, executable bit, and content SHA-256 while excluding VCS, profile, generated, and transient runtime state. The intended invariant is:

`extracted source == Docker build context == tested candidate source == materialized worktree == committed Git tree`

## Blocked ETA semantics

A `BLOCKED_RETRYABLE` attempt with no active transition no longer publishes a wall-clock completion timestamp. `pb release eta` instead reports `status=blocked_retryable`, `completion_eta_available=false`, the next blocked transition, and estimated work remaining after a future resume. ETA remains advisory and read-only.

## Retained v0.1.126.1 behavior

The publication-convergence repairs remain authoritative: exact tested-source worktree materialization, action-aware top-level publication JSON selection, durable stdout/stderr evidence, Git commit/push convergence, Project Source reconciliation including platform-assigned indexed filename families, retry reuse of verified green candidate tests, and timed publication subphases.

## Acceptance

Construction validation does not accept this release. Acceptance requires the canonical full live lifecycle to reach `FINAL_VERIFIED`, independent `release verify --all-states` to report no failed invariants, the production runtime on port 8000 to match the exact tested candidate image, Git commit/push to be verified, and the exact repair ZIP to be reconciled in Project Sources.
