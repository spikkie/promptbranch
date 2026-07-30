# Release v0.1.114.2

## Purpose

Repair the rejected `v0.1.114.1` candidate without advancing PBAI scope.

## Failure being corrected

The candidate runtime and import repair worked, including package import smoke. The first required release-validation group then failed because the exact pipx candidate Python did not contain pytest:

```text
No module named pytest
```

Fail-fast correctly skipped the remaining validation groups and adoption could not proceed.

## Repair

- Pin `pytest==9.0.2` in candidate package metadata and service requirements.
- Pin `pytest-asyncio==1.3.0` in service requirements.
- Verify pytest distribution version, module path, and interpreter prefix inside the exact pipx candidate venv before Project Source mutation.
- Export the absolute candidate Python as the release-validation interpreter.
- Preserve the venv launcher path without resolving its symlink to the base interpreter.
- Add an in-process release-validation runner preflight so standalone `pb test full` also fails closed on missing or drifted test-runner identity.
- Preserve the `v0.1.114.1` candidate-runtime binding and FastAPI/Starlette compatibility repair unchanged.

## Unchanged authority

PBAI declaration, structural, registry, executable, SkillRun evidence, operational fail-closed behavior, Project Source publication, adoption, and accepted/current verification remain unchanged.

## Acceptance

The repair requires source-tree and clean-extraction parity, isolated installed candidate proof, all required release groups, strict direct and localhost transports, external-live gates, Artifact Guardian, and exact evidence-bound adoption/current verification.
