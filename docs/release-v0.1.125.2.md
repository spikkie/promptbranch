# Promptbranch v0.1.125.2

- type: repair
- repair of: `v0.1.125.1`
- accepted/current baseline remains: `v0.1.124`
- scope advancement: forbidden

## Failure corrected

The full `v0.1.125.1` release test reached `project_authority_behavioral_surface` after the compileall repeatability repair had already passed. `test_version_projection_drift_is_detected` still attempted to replace the literal `version = "0.1.125"`, while the candidate contained `version = "0.1.125.1"`. The fixture therefore did not mutate `pyproject.toml`, and the authority validator correctly reported a consistent repository.

## Repair

- parse the actual current project version from `pyproject.toml` with `tomllib`;
- construct the exact version line from that value;
- assert the version line exists;
- replace only the first occurrence with `9.9.9`;
- assert the mutation changed the file before invoking the authority validator;
- retain the isolated `compileall` and cache-safe template snapshot repair from `v0.1.125.1`;
- keep `v0.1.125` as the active normal proof scope and `v0.1.126` as planned only after repair acceptance.

## Required proof

1. authority/behavioral validation passes;
2. project control and version surfaces pass;
3. structural → isolated compileall → structural repeatability remains green;
4. no cache or bytecode appears under `templates/pbai`;
5. mandatory release-validation groups pass;
6. deterministic ZIP and Artifact Guardian pass;
7. operator candidate lifecycle and explicit acceptance remain separate.
