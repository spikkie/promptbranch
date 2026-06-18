# Repair v0.1.78.2.8 — Docker pyproject probe quoting repair

## Context

`v0.1.78.2.7` repaired the Docker provenance probe newline JSON writer defect, but the next release-control run failed inside the running-container probe because the inline `python -c` command used to read `/app/pyproject.toml` was not shell-quoted safely.

Observed failure:

```text
SyntaxError: invalid syntax
import tomllib; print(tomllib.load(open(/app/pyproject.toml, rb))[project][version])
```

## Scope

- Replace the fragile inline Python `pyproject.toml` reader in Docker image/container probes with a shell-safe `awk` reader.
- Add a focused regression test to reject the malformed unquoted `open(/app/pyproject.toml, rb)` form.
- Preserve Docker host/image/container/health provenance checks from v0.1.78.2.6/v0.1.78.2.7.
- Preserve delete-frozen project policy.

## Out of scope

- No ChatGPT Project deletion.
- No secure delete protocol.
- No Project Source removal behavior change.
- No adoption/current mutation.
- No v0.1.79/k8s-game work.

## Validation

Focused validation before packaging:

```text
16 passed
```

Covered:

- Docker build-context/provenance guard declarations.
- Docker JSON writer newline-literal regression.
- Docker pyproject probe shell-quoting regression.
- Version tests.
- Project deletion safety tests.
- Project control-surface tests.
