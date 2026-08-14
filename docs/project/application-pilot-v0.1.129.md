# External application pilot bootstrap

## System boundary

```text
System A — Promptbranch control plane
    owns PB workflow, evidence, validation, and PB release lifecycle

System B — k8s-game-mvp pilot repository
    owns application target, architecture, tests, application artifact,
    acceptance, and later deployment authority
```

The two repositories must be physically distinct. A passing Promptbranch release never implies application acceptance.

## Pilot target

The first external pilot reuses the previously documented Kubernetes-game acceptance scenario only as a small static-browser vertical slice. The product goal of this bootstrap is not Kubernetes deployment. The visible output target is a deterministic HTML/CSS/JS browser page that can later prove controlled application change, test, candidate, and acceptance behavior.

## Read-only bootstrap contract

The bootstrap step defines, but does not write, these application-owned surfaces:

1. product target — `docs/target.md`;
2. application identity/version authority — `VERSION`;
3. application architecture — `.promptbranch-ai.json` plus `docs/architecture.md`;
4. application AI-object registry — `.promptbranch/ai-registry.json`;
5. application Definition of Done — `docs/definition-of-done.md`;
6. deterministic application test contract — `tests/test_static_game.py`;
7. one read-only execution plan that ends at `stop_before_mutation`.

## Repository prerequisite

`pb application pilot plan` accepts an explicit target repository path. It requires:

- the directory already exists;
- it differs from the Promptbranch repository;
- the configured repository marker exists;
- no Git command is executed by the planner.

Promptbranch does not create or initialize the target repository in this slice.

## Mutation authority

All mutation-related authority is false in the bootstrap contract. Human acceptance and a rollback contract are prerequisites for later mutation. The planner emits no executable mutation command and executes no application test; it only declares the future test argv.

## Next capability boundary

The next application slice may introduce explicit, bounded repository mutation only after this read-only bootstrap is accepted/current. That later change path must snapshot allowed files, prove rollback, retain human authorization, and remain separate from Promptbranch's own artifact authority.
