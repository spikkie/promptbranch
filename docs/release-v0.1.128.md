# v0.1.128 — PB environment authority cleanup, hardening and freeze

## Baseline

Accepted/current: `v0.1.127.2.1`

Artifact SHA-256: `33bbf8ca2dc458ee6c6fa9ea816cc4ca8aa9cc91b7711b9c83dc3764426f5d75`

## Scope

This normal slice performs bounded cleanup only. It removes execution-critical dual-authority and obsolete internal PB mutation paths discovered after v0.1.127 closure. It does not add release states or begin external application development.

- synchronize tracked accepted/current authority to live `v0.1.127.2.1`;
- consume only repository-loop artifact-current projections;
- root PB delegation in the exact active launcher Python and repo-local CLI;
- remove hidden `--include-controlled-writes`;
- remove executable `legacy_10_75` Project Source mutation and mutating diagnostics;
- preserve dependency compatibility, browser resilience, and fail-closed historical-state detection that do not create alternate authority.

## Construction gate

The candidate is not release-ready until all canonical release-validation groups pass against the exact final ZIP, deterministic rebuild is byte-identical, and Artifact Guardian returns `release_ready=true`.

## Live closure gate

DOD-523 requires one fresh immutable lifecycle from accepted/current `v0.1.127.2.1` through `RUNTIME_PREPARED`, `TESTED_GREEN`, `ACCEPTED`, `ADOPTED_CURRENT`, and `FINAL_VERIFIED`, with independent all-state verification and a fresh scoped `artifact current` proof.

## Next

After acceptance: `v0.1.129 — External application pilot bootstrap`.
