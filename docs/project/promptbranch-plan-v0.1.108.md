# Promptbranch plan — v0.1.108

## Slice

`v0.1.108 — Controlled correction execution envelope validation gate`

## Accepted baseline

- Accepted/current version: `v0.1.107`
- Accepted/current artifact: `chatgpt_claudecode_workflow-2_v0.1.107.zip`
- Exact assigned Project Source identity remains registry/adoption evidence and is not the canonical artifact name.

## Goal

Validate the deterministic controlled-correction execution envelope designed in `v0.1.107` without creating a workspace, executing a validation command, applying a correction, mutating a repository, or granting correction execution authority.

## Acceptance scope

- Add `pb loop execution-envelope-validation --target ... --json`.
- Load the canonical design record `docs/project/controlled-correction-execution-envelope-v0.1.107.json`.
- Recompute the envelope from the accepted target and promotion-decision inputs.
- Require exact envelope equality and exact SHA-256 fingerprint equality.
- Validate target, path, operation, hash, validation, rollback, limit, timeout, evidence, and authority constraints.
- Emit one machine-readable validation record at `docs/project/controlled-correction-execution-envelope-validation-v0.1.108.json`.
- Execute zero commands, create zero workspaces, and mutate zero files.
- Fail closed on missing, malformed, contradictory, or drifted design data.

## Authority boundary

This slice grants no correction execution, disposable-repository mutation, real-repository mutation, generic shell, deployment, Kubernetes, Project Source, artifact adoption, or ChatGPT Project deletion authority.

## Resolved roadmap collision

An earlier conversational proposal assigned `v0.1.108` to the `PROJECT_SETTINGS.md` authority model. The adopted `v0.1.107` repository control surface assigned `v0.1.108` to this execution-envelope validation gate. Repository control data is authoritative over conversation memory, so the settings/authority-model slice is renumbered.

## Next planned slice after acceptance

`v0.1.109 — PROJECT_SETTINGS.md, AGENTS.md and project authority-graph definition`

The `v0.1.109` slice will define fact-domain ownership, projections, conflict rules, and drift detection for `PROJECT_SETTINGS.md`, `AGENTS.md`, `VERSION`, repository/project identity, release configuration, plan state, artifact registries, tests, and ChatGPT Project Settings. It remains definition and read-only verification work; remote ChatGPT Project Settings mutation is out of scope.
