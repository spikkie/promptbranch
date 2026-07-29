# v0.1.112 — PBAI-001 declaration and structural validation

## Baseline

Accepted/current baseline: `v0.1.111.5.2`.

## Scope

This normal candidate implements the first bounded phase of PBAI-001:

- tracked `.promptbranch-ai.json` declaration;
- schema `promptbranch.ai.application` version `1.0`;
- `runtime_application` and `domain_module` ownership models;
- one sole version authority;
- ten required non-empty architecture layers;
- explicit generic-runtime ownership/delegation;
- bounded mutation, release, publication, and adoption authority declarations;
- bounded project-local validation command declarations;
- read-only plan and declaration/structural validation commands;
- proof-level reporting that does not overclaim;
- required release-validation integration.

## Commands

```bash
pb application architecture plan --repo-path . --json
pb application architecture validate --repo-path . --level declaration --json
pb application architecture validate --repo-path . --level structural --json
```

## Fail-closed behavior

Validation rejects unknown fields, missing or empty layers, unsafe or repeated paths, absolute paths, traversal, unsupported shell invocation, unbounded timeouts, incoherent runtime delegation, and self-granted authority.

Registry, executable, and operational proof levels are recognised but intentionally return `validation_level_not_implemented` with `proven_level=declaration` until later slices add those gates.

## Non-goals

- no registry reference resolution;
- no skill execution or SkillRun proof;
- no domain-module operational proof;
- no automatic migration of existing PB repositories;
- no closure of PBAI-001.

## Release authority

Packaging and focused validation do not establish adoption. Strict full direct and localhost validation, external-live evidence, Artifact Guardian, exact Project Source identity, registry adoption, and current verification remain required.
