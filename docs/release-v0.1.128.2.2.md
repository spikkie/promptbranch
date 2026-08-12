# v0.1.128.2.2 — Accepted-runtime baseline auto-reconciliation repair

## Purpose

Make the canonical release lifecycle self-contained at startup. A recoverable drift of the authoritative service on port 8000 must not require an operator repair command before the normal lifecycle can begin.

## Preserved behavior

- v0.1.128.2 learning/skills completeness remains unchanged.
- v0.1.128.2.1 bounded release-smoke timeout recovery remains unchanged.
- artifact/current authority remains repository-scoped, immutable and SHA-bound.

## Repair

Before isolated candidate preparation, if the accepted runtime is missing, unhealthy, or version-mismatched, Promptbranch resolves the repository's exact `adopted_release` registry record for the requested baseline and verifies kind, repo, version, SHA, ZIP integrity and embedded VERSION. It then rebuilds and restarts the authoritative compose service from those exact bytes, verifies one healthy port-8000 runtime and the adopted artifact SHA label, and only then continues. Invalid/ambiguous authority fails closed.

## Live acceptance

Construction does not accept or adopt this release. The exact artifact must reach independently verified `FINAL_VERIFIED/current` through one canonical lifecycle invocation.
