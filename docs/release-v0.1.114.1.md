# Release v0.1.114.1

## Purpose

Repair the rejected `v0.1.114` candidate without advancing PBAI scope.

## Failure being corrected

Strict host validation used `/home/spikkie/git/ai-aip/py_env/bin/pb` because that environment shadowed the freshly installed pipx candidate. `package_import_smoke` then imported an incompatible FastAPI/Starlette combination and failed with:

```text
TypeError: Router.__init__() got an unexpected keyword argument 'on_startup'
```

The same defect failed `full_direct`, `full_localhost`, and standalone `import_smoke`. Adoption was refused; `v0.1.113` remained accepted/current.

## Repair

- Bind release-critical commands to the exact pipx candidate venv.
- Verify candidate Python prefix, distribution version, `pb`, and `promptbranch` paths before Project Source mutation.
- Pass the exact candidate Python to import-smoke.
- Pin `fastapi==0.128.2` and `starlette==0.50.0` in both package and service dependencies.
- Verify those runtime dependency versions during import-smoke.
- Add shadow-PATH, interpreter-drift, and dependency-drift regressions.

## Unchanged authority

PBAI declaration, structural, registry, executable, SkillRun evidence, operational fail-closed behavior, Project Source publication, adoption, and accepted/current verification are unchanged.

## Acceptance

The repair requires source-tree and clean-extraction parity, installed candidate-runtime proof, all required release groups, strict direct and localhost transports, external-live gates, Artifact Guardian, and exact evidence-bound adoption/current verification.
