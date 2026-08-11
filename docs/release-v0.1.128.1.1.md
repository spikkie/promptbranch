# v0.1.128.1.1 — Lifecycle resume, progress, diagnostics, and control-projection repair

## Baseline

Accepted/current baseline is FINAL_VERIFIED `v0.1.128.1` with artifact SHA-256 `645bd8ce6ff388292cc29a5330786e6743bcb2ac04a419f24f274f376bf1ffa8`.

## Repair scope

- Resume the one-command lifecycle wrapper directly from `BLOCKED_RETRYABLE` without replaying already-reached states.
- Emit live state/subphase/ETA progress to stderr while keeping final `--json` stdout machine-readable.
- Separate ask route mismatch from exact-route ask timeout and exact-route ask failure.
- Synchronize tracked project control state only after authoritative `ADOPTED_CURRENT` convergence, then guarded-commit/push only the known control-projection files and verify HEAD/upstream convergence.
- Make control-surface validation compare tracked accepted/current version, artifact and SHA with the project-scoped immutable artifact registry.

## Non-goals

No new release states, providers, compatibility shims, external-application mutations, or v0.1.129 implementation.
