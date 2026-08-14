# v0.1.130 — Controlled external application change execution

Normal candidate from accepted/current `v0.1.129.1`.

## Scope

This slice converts the read-only external-application bootstrap plan into an explicitly authorized, bounded file-change capability. It supports plan, apply, and rollback only. Apply requires `--execute` plus the exact tracked change id. Before bytes are persisted outside the target repo before mutation; every after SHA-256 is verified; any partial failure triggers exact automatic rollback. Explicit rollback refuses to overwrite post-apply drift.

## Explicitly excluded

- Git command execution or publication
- ChatGPT Project Source mutation
- deployment
- application artifact adoption or acceptance
- application test execution, diagnosis, or correction (`v0.1.131`)

## Required construction proof

- application change tests and CLI tests
- project control surface
- PBAI structural/migration/pilot coverage
- version authority and exact-ZIP Docker gate
- Artifact Guardian and deterministic ZIP rebuild
- canonical normal lifecycle before accepted/current
