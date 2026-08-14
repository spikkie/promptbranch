# Release v0.1.129 — External application pilot bootstrap

## Baseline

Accepted/current Promptbranch baseline at construction start:

- version: `v0.1.128.2.7`
- artifact: `chatgpt_claudecode_workflow-2_v0.1.128.2.7.zip`
- SHA-256: `8f9876af32953e52b4154209804fd2bb5ae8c756139c9188e61c3c9144502019`

## Goal

Begin System B without granting System B mutation authority. The first pilot is the existing `k8s-game-mvp` acceptance scenario, but it must live in a repository distinct from Promptbranch and must have its own target, architecture, Definition of Done, tests, and later artifact/acceptance authority.

## New capability

`pb application pilot validate` validates the tracked pilot definition.

`pb application pilot plan --target-repo <existing-repo>` inspects an already-established external repository and emits a deterministic read-only bootstrap plan. It never initializes a repository, runs Git, writes target files, mutates Project Sources, adopts artifacts, or deploys anything.

Tracked pilot definition:

- `examples/application-pilot/k8s-game-mvp.pilot.json`
- schema: `promptbranch.application.pilot` `1.0`
- schema file: `promptbranch_protocol/schemas/application.pilot.schema.json`

The plan proposes the future application-owned surfaces:

- `VERSION`
- `.promptbranch-ai.json`
- `.promptbranch/ai-registry.json`
- `docs/target.md`
- `docs/architecture.md`
- `docs/definition-of-done.md`
- `tests/test_static_game.py`

## Authority boundary

The pilot contract requires:

- `mutation_allowed=false`
- `git_mutation_allowed=false`
- `project_source_mutation_allowed=false`
- `deployment_allowed=false`
- `acceptance_requires_human=true`
- a rollback contract before later mutation
- exactly one read-only planning iteration

The target repository must already exist, be distinct from the Promptbranch control repository, and expose its repository marker. Promptbranch does not run Git commands to discover or initialize that repository.

## Out of scope

- application file creation or editing
- Git commit/push in the external repository
- Project Source mutation for the application
- application candidate/adoption lifecycle
- Kubernetes or other deployment
- automatic acceptance

Those capabilities remain later slices, beginning with controlled external application change execution.

## Construction closure

Construction requires:

1. focused application-pilot tests;
2. project-control validation;
3. all existing required release-validation groups;
4. deterministic ZIP rebuild and Artifact Guardian;
5. exact-final-ZIP Docker build gate on a Docker-capable host before canonical lifecycle;
6. canonical normal lifecycle to `FINAL_VERIFIED/current` before acceptance is claimed.
