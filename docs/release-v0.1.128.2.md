# Release v0.1.128.2 — Promptbranch learning and skills completeness

Baseline: accepted/current `v0.1.128.1.1.1.1.1`, SHA-256 `dd9ed8949990b1b143e7930a2357adbebaccb935744a5bc30342942dbccdcdbd`.

## Purpose

Make the answer to “How does a new human, ChatGPT, Claude, or another agent learn Promptbranch itself?” complete and productized before the external-application pilot begins.

## Scope

- add canonical read-only `promptbranch-learning` and `promptbranch-operator` skills;
- add one beginner→operator→developer learning path covering mental model, authority, quickstart, operator/developer behavior, artifact authority, browser/conversation causality, release lifecycle, external-application boundary, exercises and glossary;
- add audience adapters for humans, ChatGPT Projects, Claude, generic coding agents, and PB-aware agents without creating different PB semantics;
- make the learning bundle self-contained by embedding the related canonical PB skill documents;
- generalize deterministic `pb skill export` / `pb skill verify-bundle` to learning, operator and tool-authoring bundles;
- keep every learning/operator bundle read-only, digest-bound, deterministic, tamper-detecting and explicitly non-authoritative for mutation/release/adoption/deployment;
- add canonical human entry point `docs/howto/00-learn-promptbranch.md` and README discovery.

## Validation

```sh
pb skill learning-validate --path . --json
pb skill operator-validate --path . --json
pb skill export promptbranch-learning --path . --output /tmp/promptbranch-learning.zip --json
pb skill verify-bundle /tmp/promptbranch-learning.zip --json
pb skill export promptbranch-operator --path . --output /tmp/promptbranch-operator.zip --json
pb skill verify-bundle /tmp/promptbranch-operator.zip --json
```

The release closes only after the exact `v0.1.128.2` artifact is deterministic, all canonical release-validation groups pass, Artifact Guardian is release-ready, and the normal lifecycle reaches FINAL_VERIFIED/current. After acceptance the next normal slice is `v0.1.129 — External application pilot bootstrap`.
