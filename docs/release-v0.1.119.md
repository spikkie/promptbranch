# Promptbranch v0.1.119

## Purpose

Add a deterministic, read-only planner for coordinated releases across repositories joined to one Promptbranch Project. The planner resolves dependency versions from release-set targets or accepted/current project state, checks compatibility constraints, detects cycles, and emits execution order plus parallel waves without granting rollout authority.

## Command

```bash
pb release set plan \
  --repo-path /path/to/any/joined/repo \
  --manifest /path/to/release-set.json \
  --json
```

## Contract

The manifest schema is `promptbranch.release_set` version `1.0`. Every target declares a canonical repository artifact name and version. Optional SHA-256 and repository-relative local artifact paths bind the plan to verified candidate bytes. Dependencies use a deliberately small comma-separated numeric constraint grammar: `==`, `>=`, `<=`, `>`, and `<`.

## Output

The plan contains:

- deterministic dependency-first `execution_order`;
- parallel-safe `execution_waves`;
- compatibility matrix rows with target/current resolution provenance;
- target/current artifact comparison for every repository;
- deterministic `plan_sha256`;
- explicit blockers and warnings;
- a safety proof that repository, registry, Project Source, publication, adoption, and execution state were not mutated.

## Fail-closed boundaries

Planning fails for unknown or unjoined repositories, project mismatch, duplicate repositories or dependencies, unsupported constraints, dependency cycles, missing accepted/current external dependencies, incompatible versions, noncanonical target names, invalid ZIPs, VERSION mismatch, path traversal, or SHA-256 mismatch.

A structurally valid plan can be `ok=true` while `execution_ready=false` when target artifacts are not yet locally verified and hash-bound. Guarded execution remains out of scope until `v0.1.120`.

## Next slice

`v0.1.120 — Guarded multi-repository rollout execution and rollback evidence`.
